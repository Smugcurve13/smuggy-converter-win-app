from pathlib import Path


ICON_PATH = "assets/logo.png"
ICO_ICON_PATH = "assets/icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

icon_path = Path(__file__).parent / ICON_PATH
ico_icon_path = Path(__file__).parent / ICO_ICON_PATH

# Settings live in the home dir, not the bundle: an update replaces the whole app
# directory, which would otherwise wipe the saved output folder every time.
# Same root logs.py already writes to.
APP_DATA_DIR = Path.home() / ".SmuggyConverter"
output_dir_file = APP_DATA_DIR / OUTPUT_DIR_FILE
_legacy_output_dir_file = Path(__file__).parent / OUTPUT_DIR_FILE

try:
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    # One-time migration for anyone upgrading from a build that stored it in-bundle.
    if not output_dir_file.exists() and _legacy_output_dir_file.exists():
        output_dir_file.write_text(
            _legacy_output_dir_file.read_text(encoding="utf-8"), encoding="utf-8"
        )
except OSError:
    # ponytail: a home dir we cannot write to just means the folder is re-picked
    # each launch, which _load_output_dir already handles.
    pass


import os
import shutil
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()


# Only platforms we ship a bundled binary for. Linux always uses PATH.
_BUNDLE_DIRS = {"win32": "windows", "darwin": "macos"}


def _ffmpeg_binary(name):
    """Bundled binary for this platform if we ship one, else whatever is on PATH."""
    platform_dir = _BUNDLE_DIRS.get(sys.platform)
    if platform_dir:
        suffix = ".exe" if sys.platform == "win32" else ""
        bundled = os.path.join(BASE_PATH, "assets", "ffmpeg", platform_dir, f"{name}{suffix}")
        if os.path.exists(bundled):
            return bundled
    # ponytail: bare name lets yt-dlp/ffmpeg surface its own "not found" error
    return shutil.which(name) or name


FFMPEG_PATH = _ffmpeg_binary("ffmpeg")
FFPROBE_PATH = _ffmpeg_binary("ffprobe")

# Directory handed to yt-dlp as ffmpeg_location; must hold both binaries.
FFMPEG_DIR = os.path.dirname(FFMPEG_PATH)

# _ffmpeg_binary falls back to the bare name when it finds nothing, so an
# absolute path is exactly the signal that a real binary was located.
# yt-dlp needs ffprobe as well as ffmpeg, so both must resolve.
FFMPEG_AVAILABLE = os.path.isabs(FFMPEG_PATH) and os.path.isabs(FFPROBE_PATH)


if __name__ == "__main__":
    assert _ffmpeg_binary("ffmpeg").endswith(("ffmpeg", "ffmpeg.exe")), FFMPEG_PATH
    assert _ffmpeg_binary("ffprobe").endswith(("ffprobe", "ffprobe.exe")), FFPROBE_PATH
    # A binary that cannot exist falls through to the bare name rather than None.
    assert _ffmpeg_binary("definitely-not-a-real-binary") == "definitely-not-a-real-binary"
    if sys.platform != "win32":
        assert not FFMPEG_PATH.endswith(".exe"), "must not pick the Windows exe off Windows"
    # A bare name means nothing was found, and must not read as available.
    assert FFMPEG_AVAILABLE == os.path.isabs(FFMPEG_PATH) == os.path.isabs(FFPROBE_PATH)

    # A bundled binary must win over PATH. Simulated per platform so this runs
    # anywhere, since CI is the only place a real bundle exists.
    import unittest.mock as _m

    for _plat, _dir, _sfx in (("win32", "windows", ".exe"), ("darwin", "macos", "")):
        _want = os.path.join(BASE_PATH, "assets", "ffmpeg", _dir, f"ffmpeg{_sfx}")
        with _m.patch.object(sys, "platform", _plat), \
             _m.patch("os.path.exists", lambda p, _w=_want: p == _w):
            assert _ffmpeg_binary("ffmpeg") == _want, f"{_plat}: got {_ffmpeg_binary('ffmpeg')}"
        # With no bundle present it must fall through rather than invent a path.
        # shutil.which is stubbed because it consults _winapi under a faked win32.
        with _m.patch.object(sys, "platform", _plat), \
             _m.patch("os.path.exists", lambda p: False), \
             _m.patch("shutil.which", lambda n: "/usr/bin/" + n):
            assert _ffmpeg_binary("ffmpeg") == "/usr/bin/ffmpeg"

    # Linux ships no bundle, so it must never claim one even if the path exists.
    with _m.patch.object(sys, "platform", "linux"), \
         _m.patch("os.path.exists", lambda p: True), \
         _m.patch("shutil.which", lambda n: "/usr/bin/" + n):
        assert _ffmpeg_binary("ffmpeg") == "/usr/bin/ffmpeg"

    print(f"ffmpeg : {FFMPEG_PATH}\nffprobe: {FFPROBE_PATH}\ndir    : {FFMPEG_DIR}")
    print(f"available: {FFMPEG_AVAILABLE}")