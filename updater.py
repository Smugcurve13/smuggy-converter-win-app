"""Poll GitHub releases, download the new build, and swap it in on restart.

The app ships as a PyInstaller --onedir bundle inside a plain zip, so an update
replaces a whole directory (Windows) or .app bundle (macOS). A running process
cannot delete its own directory, so the swap runs from a small detached helper
that waits for us to exit first.

Division of labour: this module downloads, verifies and extracts while the GUI
shows progress and can report real errors. The helper only renames and
relaunches — rename aside, rename in, delete aside — so a failure at any step
is recoverable.
"""

from pathlib import Path
import json
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

import certifi
from packaging.version import InvalidVersion, Version

from logs import logger
from version import __version__

REPO = "Smugcurve13/smuggy-converter-win-app"
LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"

_UA = f"SmuggyConverter/{__version__}"
# GitHub answers 403 to a request without a User-Agent.
_API_HEADERS = {"User-Agent": _UA, "Accept": "application/vnd.github+json"}
_ASSET_HEADERS = {"User-Agent": _UA, "Accept": "application/octet-stream"}

# Only platforms CI publishes an asset for, matched as a substring of the asset
# name, e.g. SmuggyConverter-macos-arm64-v1.3.0.zip.
_ASSET_TAGS = {"win32": "windows", "darwin": "macos"}

_CHUNK = 1 << 20
# Short on purpose: PySide6 paths are deep and PyInstaller's manifest is not
# longPathAware, so a verbose staging name can push extraction past MAX_PATH.
_STAGING_NAME = ".upd"
# Zip, plus the extracted copy, plus the old copy still on disk during the swap.
_FREE_SPACE_FLOOR = 1_000_000_000


def _ssl_context() -> ssl.SSLContext:
    # Frozen macOS builds have no OpenSSL cert dir and Python's ssl does not
    # read the Keychain, so the system store is not an option there. certifi is
    # imported explicitly rather than relying on yt-dlp dragging it in.
    return ssl.create_default_context(cafile=certifi.where())


def app_root() -> Path | None:
    """The directory an update would replace, or None when not updatable.

    Running from source returns None — there is nothing to swap.
    """
    if not (getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")):
        return None
    exe = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        # .../SmuggyConverter.app/Contents/MacOS/SmuggyConverter
        for parent in exe.parents:
            if parent.suffix == ".app":
                return parent
    return exe.parent


def blocked_reason(needed_bytes: int = 0) -> str | None:
    """Why an in-app update cannot work here, or None if it can.

    Checked before downloading 140 MB so a doomed update fails in a dialog
    rather than after the transfer.
    """
    app = app_root()
    if app is None:
        return "In-app updates only work in a released build."

    # A quarantined .app opened from Downloads runs from a read-only randomized
    # path and cannot tell where it really lives. The README's right-click-Open
    # instructions lead straight here.
    if "/AppTranslocation/" in str(app):
        return ("SmuggyConverter is running from a temporary read-only copy.\n"
                "Move it to your Applications folder, reopen it, then update.")

    # Explorer happily runs an exe straight out of a zip preview, into a temp
    # folder that evaporates. Updating that would update nothing.
    tmp = Path(tempfile.gettempdir()).resolve()
    if tmp == app.parent or tmp in app.parents:
        return ("SmuggyConverter is running from a temporary folder.\n"
                "Extract the zip somewhere permanent, then update.")

    # os.access(W_OK) only reports the read-only attribute on Windows and says
    # yes for Program Files under a standard user, so probe for real. This also
    # catches read-only volumes and Controlled Folder Access.
    probe = app.parent / f".upd-probe-{os.getpid()}"
    try:
        probe.mkdir()
        probe.rmdir()
    except OSError:
        return (f"SmuggyConverter cannot write to {app.parent}.\n"
                "Move it somewhere you own, or update manually.")

    try:
        free = shutil.disk_usage(app.parent).free
    except OSError:
        free = _FREE_SPACE_FLOOR
    if free < max(_FREE_SPACE_FLOOR, needed_bytes * 4):
        return "Not enough free disk space to install the update."

    return None


def _is_newer(tag: str, current: str = __version__) -> bool:
    """Tags carry a leading v, version.py does not."""
    try:
        return Version(tag.lstrip("vV")) > Version(current)
    except InvalidVersion:
        logger.warning("Unparseable release tag, ignoring", extra={"tag": tag})
        return False


def _pick_asset(assets: list[dict]) -> dict | None:
    tag = _ASSET_TAGS.get(sys.platform)
    if not tag:
        return None
    for asset in assets:
        name = asset.get("name", "")
        if tag in name and name.endswith(".zip"):
            return asset
    return None


def check() -> dict | None:
    """Latest release if it is newer than us and has an asset for this platform.

    Never raises: a failed check is a non-event, the app carries on.
    """
    if app_root() is None:
        return None
    _sweep()
    try:
        req = urllib.request.Request(LATEST_URL, headers=_API_HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=_ssl_context()) as resp:
            release = json.load(resp)
    except Exception as exc:
        logger.warning("Update check failed", extra={"error": str(exc)})
        return None

    tag = release.get("tag_name", "")
    if not _is_newer(tag):
        logger.info("Already on the latest version", extra={"latest": tag})
        return None

    asset = _pick_asset(release.get("assets", []))
    if asset is None:
        logger.warning("No release asset for this platform", extra={"tag": tag})
        return None

    logger.info("Update available", extra={"latest": tag, "current": __version__})
    return {
        "version": tag,
        "url": asset["browser_download_url"],
        "size": asset.get("size", 0),
        "notes_url": release.get("html_url", RELEASES_URL),
    }


def _sweep() -> None:
    """Drop leftovers from an update that failed partway. Best effort."""
    app = app_root()
    if app is None:
        return
    for junk in (Path(f"{app}.old"), app.parent / _STAGING_NAME):
        if junk.exists():
            logger.info("Removing stale update leftovers", extra={"path": str(junk)})
            shutil.rmtree(junk, ignore_errors=True)


def download(url: str, dest: Path, progress_callback=None, is_cancelled=None) -> bool:
    """Stream the release zip to dest. False means the caller cancelled."""
    req = urllib.request.Request(url, headers=_ASSET_HEADERS)
    # browser_download_url 302s to the release CDN; the default opener follows it.
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        with open(dest, "wb") as out:
            while chunk := resp.read(_CHUNK):
                if is_cancelled is not None and is_cancelled():
                    out.close()
                    dest.unlink(missing_ok=True)
                    logger.info("Update download cancelled")
                    return False
                out.write(chunk)
                read += len(chunk)
                if progress_callback and total:
                    progress_callback(int(read / total * 100))

    # Verify before anything destructive happens. Reading the central directory
    # is instant and catches a truncated transfer; testzip() would decompress
    # all 140 MB to learn the same thing.
    if total and read != total:
        raise OSError(f"download truncated: got {read} of {total} bytes")
    with zipfile.ZipFile(dest) as zf:
        if not _top_level(zf.namelist()):
            raise OSError("downloaded archive has an unexpected layout")

    logger.info("Update downloaded", extra={"bytes": read, "dest": str(dest)})
    return True


def _top_level(names: list[str]) -> str | None:
    """The single root entry in the archive, or None if it isn't single."""
    tops = {n.split("/", 1)[0] for n in names} - {"__MACOSX", ""}
    return tops.pop() if len(tops) == 1 else None


def _extract(zip_path: Path, staging: Path) -> Path:
    """Unpack into staging and return the app directory inside it."""
    if sys.platform == "darwin":
        # zipfile writes symlinks as plain text files and drops the exec bit,
        # which silently produces an .app that will not launch — the same
        # reason the release workflow zips with ditto rather than zip.
        # --noqtn: a quarantined app propagates quarantine to what it extracts,
        # and the result would be an unnotarized bundle Gatekeeper refuses.
        subprocess.run(
            ["/usr/bin/ditto", "-x", "-k", "--noqtn", str(zip_path), str(staging)],
            check=True,
            capture_output=True,
        )
    else:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(staging)

    entries = [p for p in staging.iterdir() if not p.name.startswith(("__MACOSX", "."))]
    if len(entries) != 1:
        raise RuntimeError(f"unexpected archive layout: {[p.name for p in entries]}")
    return entries[0]


# Both helpers take their paths as arguments rather than interpolated text, so a
# folder name containing % or a quote cannot rewrite the script.
_WINDOWS_HELPER = r"""@echo off
setlocal
set "PID=%~1"
set "APP=%~2"
set "NEW=%~3"
set "EXE=%~4"
set "STAGING=%~5"

set /a n=0
:wait
tasklist /FI "PID eq %PID%" /NH 2>nul | find "%PID%" >nul || goto gone
set /a n+=1
if %n% GEQ 120 goto fail
rem ping, not timeout: timeout aborts with "Input redirection is not supported"
rem when the launching process has no console, which a --windowed app has not.
ping -n 2 127.0.0.1 >nul
goto wait

:gone
rem Let Defender finish scanning the freshly written files before we rename.
ping -n 3 127.0.0.1 >nul
rem "move src dst" moves INTO dst when dst already exists as a directory.
rd /s /q "%APP%.old" 2>nul
move "%APP%" "%APP%.old" >nul 2>&1 || goto fail
move "%NEW%" "%APP%" >nul 2>&1 || goto rollback
start "" "%EXE%"
rd /s /q "%APP%.old" >nul 2>&1
rd /s /q "%STAGING%" >nul 2>&1
goto done

:rollback
move "%APP%.old" "%APP%" >nul 2>&1
:fail
start "" "%EXE%"
:done
rem Drops the batch context so cmd releases the file and the delete succeeds.
(goto) 2>nul & del "%~f0"
"""

_MACOS_HELPER = r"""#!/bin/sh
PID="$1"; APP="$2"; NEW="$3"; STAGING="$4"
n=0
while kill -0 "$PID" 2>/dev/null; do
  n=$((n+1)); [ "$n" -gt 240 ] && break
  sleep 0.5
done
OLD="$APP.old"
rm -rf "$OLD"
mv "$APP" "$OLD" 2>/dev/null || { open -n "$APP"; rm -f "$0"; exit 1; }
if mv "$NEW" "$APP"; then
  # Belt and braces on top of ditto --noqtn; never gate on its exit code,
  # /usr/bin/xattr was a python shim on older macOS.
  xattr -dr com.apple.quarantine "$APP" 2>/dev/null
  open -n "$APP"
  rm -rf "$OLD" "$STAGING"
else
  mv "$OLD" "$APP"
  open -n "$APP"
fi
rm -f "$0"
"""


def apply(zip_path: Path) -> None:
    """Stage the new build and hand the swap to a detached helper.

    Returns as soon as the helper is running; the caller must then quit so the
    helper can replace the directory and relaunch.
    """
    app = app_root()
    if app is None:
        raise RuntimeError("not a frozen build")

    # Sibling of the app, so the helper's renames stay on one volume and cannot
    # fail halfway through a copy.
    staging = app.parent / _STAGING_NAME
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    new = _extract(zip_path, staging)

    pid = os.getpid()
    if sys.platform == "win32":
        body, suffix = _WINDOWS_HELPER, ".cmd"
        args = [str(pid), str(app), str(new), str(app / Path(sys.executable).name), str(staging)]
    else:
        body, suffix = _MACOS_HELPER, ".sh"
        args = [str(pid), str(app), str(new), str(staging)]

    # Written to temp, never inside the app: no release.yaml change, and no
    # extra unsigned file inside the macOS bundle.
    fd, script = tempfile.mkstemp(prefix="smuggy-update-", suffix=suffix)
    with os.fdopen(fd, "w", newline="") as fh:
        fh.write(body)

    logger.info("Launching update helper", extra={"script": script, "pid": pid})
    if sys.platform == "win32":
        # CREATE_NO_WINDOW, not DETACHED_PROCESS: the latter leaves the helper
        # with no console at all, and is documented to override the former.
        # Windows children outlive their parent either way.
        subprocess.Popen(
            ["cmd", "/c", script, *args],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    else:
        os.chmod(script, 0o755)
        subprocess.Popen(
            ["/bin/sh", script, *args],
            start_new_session=True,
            close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    import unittest.mock as _m

    # Tags carry a v and version.py does not; that mismatch is the whole risk here.
    assert _is_newer("v1.4.0", "1.3.0")
    assert _is_newer("1.4.0", "1.3.0")
    assert _is_newer("v1.3.1", "1.3.0")
    assert not _is_newer("v1.3.0", "1.3.0")
    assert not _is_newer("v1.2.9", "1.3.0")
    assert not _is_newer("v1.10.0", "1.11.0"), "must compare numerically, not as strings"
    assert _is_newer("v1.11.0", "1.10.0")
    # A junk tag must read as "no update", never crash the launch path.
    assert not _is_newer("not-a-version", "1.3.0")

    _ASSETS = [
        {"name": "SmuggyConverter-windows-v1.3.0.zip", "browser_download_url": "w"},
        {"name": "SmuggyConverter-macos-arm64-v1.3.0.zip", "browser_download_url": "m"},
    ]
    for _plat, _want in (("win32", "w"), ("darwin", "m")):
        with _m.patch.object(sys, "platform", _plat):
            assert _pick_asset(_ASSETS)["browser_download_url"] == _want, _plat
    # A platform we publish nothing for must decline rather than pick a wrong zip.
    with _m.patch.object(sys, "platform", "linux"):
        assert _pick_asset(_ASSETS) is None
    with _m.patch.object(sys, "platform", "darwin"):
        assert _pick_asset([{"name": "SmuggyConverter-windows-v1.3.0.zip"}]) is None

    # Both release zips carry exactly one root entry; ditto adds no __MACOSX
    # here, but strip it anyway since that depends on --sequesterRsrc.
    assert _top_level(["SmuggyConverter/x.exe", "SmuggyConverter/_internal/y"]) == "SmuggyConverter"
    assert _top_level(["SmuggyConverter.app/Contents/MacOS/z", "__MACOSX/._a"]) == "SmuggyConverter.app"
    assert _top_level(["a/x", "b/y"]) is None, "an ambiguous archive must be rejected"

    # Unfrozen means unupdatable, and check() must short-circuit before the network.
    assert app_root() is None
    assert check() is None
    assert blocked_reason() is not None

    # A .app is found by walking up to the bundle, not by a fixed parent count.
    with _m.patch.object(sys, "platform", "darwin"), \
         _m.patch.object(sys, "frozen", True, create=True), \
         _m.patch.object(sys, "_MEIPASS", "/A/S.app/Contents/Frameworks", create=True), \
         _m.patch.object(sys, "executable", "/A/S.app/Contents/MacOS/S"):
        assert app_root() == Path("/A/S.app"), app_root()
        # Translocation must be refused rather than "updating" a read-only copy.
        with _m.patch.object(sys, "executable",
                             "/private/var/folders/x/AppTranslocation/u/d/S.app/Contents/MacOS/S"):
            assert "read-only copy" in blocked_reason()

    # Rename aside must precede rename in, else a failure leaves no app at all.
    assert _MACOS_HELPER.index('mv "$APP" "$OLD"') < _MACOS_HELPER.index('mv "$NEW" "$APP"')
    assert _WINDOWS_HELPER.index('move "%APP%" "%APP%.old"') < _WINDOWS_HELPER.index('move "%NEW%" "%APP%"')
    # timeout needs a console the helper does not have.
    assert "timeout /t" not in _WINDOWS_HELPER
    # move would nest the app inside a surviving .old directory.
    assert _WINDOWS_HELPER.index('rd /s /q "%APP%.old" 2>nul') < _WINDOWS_HELPER.index('move "%APP%"')

    print(f"current version : {__version__}")
    print(f"platform asset  : {_ASSET_TAGS.get(sys.platform, '(unsupported)')}")
    # Live check, bypassing the frozen guard so the network path is exercised.
    with _m.patch(f"{__name__}.app_root", lambda: Path.cwd()):
        print(f"latest release  : {check()}")
