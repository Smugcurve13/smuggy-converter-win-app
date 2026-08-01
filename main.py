from pathlib import Path
import platform
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QSystemTrayIcon,
)

from gui.converter_window import ConverterWindow
from config import icon_path, FFMPEG_AVAILABLE, FFMPEG_PATH
from logs import logger

logger.info("Application started.")

_INSTALL_HINT = {
    "Darwin": "Install it with:\n\n    brew install ffmpeg",
    "Linux": "Install it with:\n\n    sudo apt install ffmpeg",
}.get(platform.system(), "Try reinstalling SmuggyConverter — ffmpeg ships with it.")


def resource_path(name):
    base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).parent
    return base / "assets" / name


def _require_ffmpeg() -> None:
    """Fail at startup with a clear message rather than mid-conversion."""
    if FFMPEG_AVAILABLE:
        return
    logger.error("ffmpeg not found at startup", extra={"resolved": FFMPEG_PATH})
    box = QMessageBox()
    box.setWindowTitle("FFmpeg not found")
    box.setIcon(QMessageBox.Critical)
    box.setText("SmuggyConverter needs FFmpeg to convert audio and video.")
    box.setInformativeText(f"{_INSTALL_HINT}\n\nThen restart SmuggyConverter.")
    box.setStandardButtons(QMessageBox.Ok)
    box.exec()
    sys.exit(1)


def main() -> None:
    app = QApplication([])
    app.setWindowIcon(QIcon(str(icon_path)))
    _require_ffmpeg()
    window = ConverterWindow()
    window.showMaximized()
    tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), parent=None)
    tray_icon.show()
    app.exec()


if __name__ == "__main__":
    main()
