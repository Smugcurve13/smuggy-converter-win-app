from pathlib import Path

from PySide6.QtCore import QThread, Signal

from audio_trim import trim_audio


class AudioTrimWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, source: Path, start_seconds: float, end_seconds: float, destination: Path, parent=None):
        super().__init__(parent)
        self.source = Path(source)
        self.start_seconds = start_seconds
        self.end_seconds = end_seconds
        self.destination = Path(destination)

    def run(self):
        try:
            saved = trim_audio(self.source, self.start_seconds, self.end_seconds, self.destination)
        except Exception as exc:
            self.finished.emit(False, str(exc))
            return
        self.finished.emit(True, str(saved))
