from pathlib import Path

ICON_PATH = "assets/logo.png"
ICO_ICON_PATH = "assets/icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

icon_path = Path(__file__).parent / ICON_PATH
ico_icon_path = Path(__file__).parent / ICO_ICON_PATH
output_dir_file = Path(__file__).parent / OUTPUT_DIR_FILE