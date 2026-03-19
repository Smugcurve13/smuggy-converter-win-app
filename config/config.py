from pathlib import Path


ICON_PATH = "assets/logo.png"
ICO_ICON_PATH = "assets/icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

icon_path = Path(__file__).parent / ICON_PATH
ico_icon_path = Path(__file__).parent / ICO_ICON_PATH
output_dir_file = Path(__file__).parent / OUTPUT_DIR_FILE


import os
import sys

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

FFMPEG_PATH = os.path.join(BASE_PATH, "assets", "ffmpeg", "windows", "ffmpeg.exe")
FFPROBE_PATH = os.path.join(BASE_PATH, "assets", "ffmpeg", "windows", "ffprobe.exe")