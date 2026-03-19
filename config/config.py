from pathlib import Path


ICON_PATH = "assets/logo.png"
ICO_ICON_PATH = "assets/icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

# config/ is one level below the project root, so navigate up two levels
_PROJECT_ROOT = Path(__file__).parent.parent

icon_path = _PROJECT_ROOT / ICON_PATH
ico_icon_path = _PROJECT_ROOT / ICO_ICON_PATH
output_dir_file = _PROJECT_ROOT / OUTPUT_DIR_FILE


import os
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    # Go up two levels: config/config.py -> config/ -> project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_PATH = get_base_path()

FFMPEG_PATH = os.path.join(BASE_PATH, "assets", "ffmpeg", "windows", "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BASE_PATH, "assets", "ffmpeg", "windows", "ffprobe.exe")