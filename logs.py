import logging
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import platform
import zipfile
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from config import FFMPEG_PATH, FFPROBE_PATH
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

# Static base name: the handler appends the date on rollover. Putting the date in
# the base name too produced smuggyconverter_logs_2026-07-31.txt.2026-08-01.txt and
# stopped backupCount from ever pruning.
file = pathlib.Path(f"{folder}/smuggyconverter.log")

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

# logging only renders `extra` fields a format string names, so every
# logger.error(..., extra={"error": e}) in this codebase used to vanish. Appending
# the non-standard record attributes here fixes all of those call sites at once.
_STD_RECORD_KEYS = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime", "taskName"}


class ExtraFormatter(logging.Formatter):
    def format(self, record):
        base = super().format(record)
        extras = {k: v for k, v in record.__dict__.items() if k not in _STD_RECORD_KEYS}
        return f"{base} | {extras}" if extras else base


formatter = ExtraFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Configure yt-dlp logger to capture warnings and errors
ytdlp_logger = logging.getLogger('yt_dlp')
ytdlp_logger.setLevel(logging.DEBUG)
ytdlp_logger.addHandler(file_handler)

def _ytdlp_version() -> str:
    try:
        from yt_dlp.version import __version__ as v

        return v
    except Exception:
        return "unknown"


def _js_runtimes() -> str:
    """yt-dlp leans on a JS runtime for some extractors; note which are present."""
    found = []
    for runtime in ("node", "bun", "deno"):
        if not shutil.which(runtime):
            continue
        try:
            out = subprocess.run(
                [runtime, "--version"],
                capture_output=True, text=True, timeout=2,
                # Keeps a console window from flashing on Windows.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            found.append(f"{runtime} {out.stdout.strip().splitlines()[0]}")
        except Exception:
            found.append(f"{runtime} (detected)")
    return ", ".join(found) if found else "None detected"


# Diagnostics worth having in a support log. Deliberately no public-IP lookup:
# it is PII in a file users email us, and it puts a network call on startup.
logger.info("=" * 60)
logger.info("SmuggyConverter initialized")
logger.info("Version      : %s", __version__)
logger.info("OS           : %s %s", platform.system(), platform.version())
logger.info("Date / Time  : %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
logger.info("Hostname     : %s", socket.gethostname())
logger.info("Python       : %s", sys.version.replace("\n", " "))
logger.info("Executable   : %s", sys.executable)
logger.info("Frozen       : %s", bool(getattr(sys, "frozen", False)))
logger.info("yt-dlp       : %s", _ytdlp_version())
logger.info("ffmpeg       : %s", FFMPEG_PATH)
logger.info("ffprobe      : %s", FFPROBE_PATH)
logger.info("JS runtimes  : %s", _js_runtimes())
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


def default_zip_path() -> str:
    """Return a suggested absolute path for the exported zip.

    Absolute on purpose: a bare filename is resolved against the process's
    working directory, which is "/" for an app launched from Finder, and the
    save dialog then defaults to a read-only filesystem.
    """
    name = f"smuggyconverter_logs_{datetime.now().strftime('%Y-%m-%d')}.zip"
    return os.path.join(home_folder, name)


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