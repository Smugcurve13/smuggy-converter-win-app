"""Synchronize the pinned yt-dlp release and app patch version."""

import argparse
import json
import re
import urllib.request
from pathlib import Path


_UPSTREAM_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
_YTDLP = re.compile(r"^yt-dlp==([^\s]+)$", re.MULTILINE)
_APP_VERSION = re.compile(r'^__version__ = "(\d+)\.(\d+)\.(\d+)"$', re.MULTILINE)


def _parts(version: str) -> tuple[int, ...]:
    version = version.lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+)+", version):
        raise ValueError(f"unsupported numeric version: {version}")
    return tuple(int(part) for part in version.split("."))


def has_newer_release(latest: str, current: str) -> bool:
    return _parts(latest) > _parts(current)


def latest_release() -> str:
    request = urllib.request.Request(
        _UPSTREAM_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "SmuggyConverter-sync"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        tag = json.load(response)["tag_name"]
    _parts(tag)
    return tag.lstrip("vV")


def _current_ytdlp(root: Path) -> str:
    match = _YTDLP.search((root / "requirements.txt").read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("requirements.txt does not pin yt-dlp")
    return match.group(1)


def apply_release(root: Path, upstream_version: str) -> str:
    upstream_version = upstream_version.lstrip("vV")
    _parts(upstream_version)
    requirements_path = root / "requirements.txt"
    requirements = requirements_path.read_text(encoding="utf-8")
    if _YTDLP.search(requirements) is None:
        raise ValueError("requirements.txt does not pin yt-dlp")
    requirements_path.write_text(
        _YTDLP.sub(f"yt-dlp=={upstream_version}", requirements, count=1), encoding="utf-8"
    )

    version_path = root / "version.py"
    version_source = version_path.read_text(encoding="utf-8")
    match = _APP_VERSION.search(version_source)
    if match is None:
        raise ValueError("version.py must contain a stable X.Y.Z version")
    app_version = f"{match.group(1)}.{match.group(2)}.{int(match.group(3)) + 1}"
    version_path.write_text(
        _APP_VERSION.sub(f'__version__ = "{app_version}"', version_source, count=1), encoding="utf-8"
    )

    notes_path = root / "release_notes.py"
    notes = notes_path.read_text(encoding="utf-8")
    marker = "NOTES = {\n"
    if marker not in notes:
        raise ValueError("release_notes.py does not define NOTES")
    entry = (
        f'    "{app_version}": {{\n'
        '        "NEW": [],\n'
        '        "CHANGED": [\n'
        f'            "Updated yt-dlp core to v{upstream_version}.",\n'
        '        ],\n'
        '        "FIXED": [],\n'
        '    },\n'
    )
    notes_path.write_text(notes.replace(marker, marker + entry, 1), encoding="utf-8")
    return app_version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--upstream-version")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    latest = (args.upstream_version or latest_release()).lstrip("vV")
    current = _current_ytdlp(root)
    if not has_newer_release(latest, current):
        print(f"yt-dlp is current: {current}")
        return
    if not args.apply:
        print(f"yt-dlp update available: {current} -> {latest}")
        return
    print(f"yt-dlp updated: {current} -> {latest}; app version: {apply_release(root, latest)}")


if __name__ == "__main__":
    main()
