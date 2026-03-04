import logging
import os
import pathlib
import sys
import subprocess
#create dir, create file , initialise logger with formatting , add levels , apply logger to file .

FILENAME = "logs.txt"
FOLDERNAME = ".SmuggyConverter/logs"

home_folder = subprocess.run("echo $HOME", shell=True, capture_output=True, text=True).stdout.strip()
folder = f"{home_folder}/{FOLDERNAME}"

if not os.path.exists(folder):
    os.makedirs(folder, exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file = pathlib.Path(f"{folder}/{FILENAME}")
file_handler = logging.FileHandler(file)
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

# Configure yt-dlp logger to capture warnings and errors
ytdlp_logger = logging.getLogger('yt_dlp')
ytdlp_logger.setLevel(logging.DEBUG)
ytdlp_logger.addHandler(file_handler)

logger.info("Logger initialized") 


# import logging
# import os
# import pathlib

# FILENAME = "logs.txt"
# FOLDERNAME = ".SmuggyConverter/logs"

# # ✅ Cross-platform home directory
# home_folder = os.path.expanduser("~")

# folder = os.path.join(home_folder, FOLDERNAME)

# os.makedirs(folder, exist_ok=True)

# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)

# file_path = pathlib.Path(os.path.join(folder, FILENAME))

# file_handler = logging.FileHandler(file_path, encoding="utf-8")
# file_handler.setLevel(logging.DEBUG)

# formatter = logging.Formatter(
#     "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
# )
# file_handler.setFormatter(formatter)

# logger.addHandler(file_handler)

# # Configure yt-dlp logger
# ytdlp_logger = logging.getLogger("yt_dlp")
# ytdlp_logger.setLevel(logging.DEBUG)
# ytdlp_logger.addHandler(file_handler)

# logger.info("Logger initialized")