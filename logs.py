import logging
import os
import pathlib
import subprocess
import platform
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

def export_logs():
    # opens export dialog and allows user to select location to save logs.txt
    if platform.system() == "Windows":
        subprocess.run(f'explorer /select,"{file}"')
    elif platform.system() == "Darwin":  # macOS
        subprocess.run(["open", "-R", file])
    else:  # Linux
        subprocess.run(["xdg-open", folder])

if __name__ == "__main__":
    export_logs()