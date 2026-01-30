import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit
)
from PySide6.QtCore import Signal, QObject
import yt_dlp


class WorkerSignals(QObject):
    log = Signal(str)


class Downloader:
    def __init__(self, signals):
        self.signals = signals

    def run(self, url, fmt):
        def hook(d):
            if d["status"] == "downloading":
                self.signals.log.emit(d.get("_percent_str", "").strip())
            elif d["status"] == "finished":
                self.signals.log.emit("Download complete. Post-processing...")

        ydl_opts = {
            "format": "bestaudio/best" if fmt == "mp3" else "best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }] if fmt == "mp3" else [],
            "progress_hooks": [hook],
            "outtmpl": "%(title)s.%(ext)s",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.signals.log.emit("Done.")
        except Exception as e:
            self.signals.log.emit(f"Error: {str(e)}")


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmuggyConverter Prototype")
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("YouTube URL"))
        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)

        row = QHBoxLayout()
        self.format_box = QComboBox()
        self.format_box.addItems(["mp3", "mp4"])
        row.addWidget(QLabel("Format"))
        row.addWidget(self.format_box)
        layout.addLayout(row)

        self.button = QPushButton("Convert & Download")
        self.button.clicked.connect(self.start)
        layout.addWidget(self.button)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)

    def start(self):
        url = self.url_input.text().strip()
        if not url:
            self.log.append("No URL provided.")
            return

        fmt = self.format_box.currentText()

        self.signals = WorkerSignals()
        self.signals.log.connect(self.log.append)

        self.log.append("Starting...")
        worker = Downloader(self.signals)

        thread = threading.Thread(target=worker.run, args=(url, fmt), daemon=True)
        thread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
