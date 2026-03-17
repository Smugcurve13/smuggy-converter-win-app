import logging
import os
import pathlib
import subprocess
import platform
import zipfile
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from version import __version__

#create dir, create file , initialise logger with formatting , add levels , apply logger to file .

FOLDERNAME = ".SmuggyConverter/logs"

# Check OS and use appropriate environment variable
if platform.system() == "Windows":
    home_folder = os.environ.get("USERPROFILE", os.path.expanduser("~"))
else:  # macOS and Linux
    home_folder = os.environ.get("HOME", os.path.expanduser("~"))
folder = f"{home_folder}/{FOLDERNAME}"

if not os.path.exists(folder):
    os.makedirs(folder, exist_ok=True)

# Build today's log filename: smuggyconverter_logs_YYYY-MM-DD.txt
today_str = datetime.now().strftime("%Y-%m-%d")
log_filename = f"smuggyconverter_logs_{today_str}.txt"
file = pathlib.Path(f"{folder}/{log_filename}")

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# TimedRotatingFileHandler rotates at midnight, creating a new file each day.
# The base file always represents today; backups get a date suffix appended.
file_handler = TimedRotatingFileHandler(
    file,
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8",
)
file_handler.suffix = "%Y-%m-%d.txt"
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Configure yt-dlp logger to capture warnings and errors
ytdlp_logger = logging.getLogger('yt_dlp')
ytdlp_logger.setLevel(logging.DEBUG)
ytdlp_logger.addHandler(file_handler)

logger.info("=" * 60)
logger.info("SmuggyConverter initialized")
logger.info("Version      : %s", __version__)
logger.info("OS           : %s %s", platform.system(), platform.version())
logger.info("Date / Time  : %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
logger.info("=" * 60)

def create_logs_zip(dest_path: str) -> pathlib.Path:
    """Zip all log files in the logs folder into dest_path.

    dest_path should be the full path to the target .zip file.
    Returns the Path of the created zip.
    """
    zip_path = pathlib.Path(dest_path)
    log_dir = pathlib.Path(folder)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for log_file in sorted(log_dir.iterdir()):
            if log_file.is_file():
                zf.write(log_file, log_file.name)
    return zip_path


def default_zip_name() -> str:
    """Return a suggested zip filename based on today's date."""
    return f"smuggyconverter_logs_{datetime.now().strftime('%Y-%m-%d')}.zip"


def export_logs():
    """Legacy helper: open the logs folder in the OS file manager."""
    if platform.system() == "Windows":
        os.startfile(str(folder))
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["open", str(folder)])
    else:  # Linux
        subprocess.run(["xdg-open", str(folder)])

if __name__ == "__main__":
    export_logs()