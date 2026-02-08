import logging
import os
import pathlib
import sys
import subprocess
#create dir, create file , initialise logger with formatting , add levels , apply logger to file .

FILENAME = "logs.txt"
FOLDERNAME = "SmuggyConverter_logs"

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

logger.info("Logger initialized") 