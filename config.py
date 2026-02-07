from pathlib import Path

ICON_PATH = "logo.png"
ICO_ICON_PATH = "icon.ico"
OUTPUT_DIR_FILE = "output_dir.txt"

icon_path = Path(__file__).with_name(ICON_PATH)
ico_icon_path = Path(__file__).with_name(ICO_ICON_PATH)
output_dir_file = Path(__file__).with_name(OUTPUT_DIR_FILE)