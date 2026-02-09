from pathlib import Path
import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
)

from gui.converter_window import ConverterWindow
from config import icon_path
from logs import logger
from core.ffmpeg_resolver import get_ffmpeg_path

logger.info("Application started.")

try:
    print("Using ffmpeg at:", get_ffmpeg_path())
except Exception as e:
    print(str(e))
    sys.exit(1)

def resource_path(name):
    base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).parent
    return base / "assets" / name

def main() -> None:
    app = QApplication([])
    app.setWindowIcon(QIcon(str(icon_path)))
    window = ConverterWindow()
    window.showMaximized()
    tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), parent=None)
    tray_icon.show()
    app.exec()


if __name__ == "__main__":
    main()
