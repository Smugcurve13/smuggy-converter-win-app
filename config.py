from pathlib import Path


ICON_PATH = "assets/logo.png"
ICO_ICON_PATH = "assets/icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

icon_path = Path(__file__).parent / ICON_PATH
ico_icon_path = Path(__file__).parent / ICO_ICON_PATH
output_dir_file = Path(__file__).parent / OUTPUT_DIR_FILE


import os
import shutil
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()


def _ffmpeg_binary(name):
    """Bundled Windows binary when running on Windows, else whatever is on PATH."""
    bundled = os.path.join(BASE_PATH, "assets", "ffmpeg", "windows", f"{name}.exe")
    if sys.platform == "win32" and os.path.exists(bundled):
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
    print(f"ffmpeg : {FFMPEG_PATH}\nffprobe: {FFPROBE_PATH}\ndir    : {FFMPEG_DIR}")
    print(f"available: {FFMPEG_AVAILABLE}")