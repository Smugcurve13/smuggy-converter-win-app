from pathlib import Path

from PySide6.QtCore import QThread, Signal

from music_analysis import analyze_file


class MusicAnalysisWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(list, list, bool)  # rows, failed filenames, cancelled

    def __init__(self, paths: list[Path], parent=None):
        super().__init__(parent)
        self.paths = list(paths)
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def run(self):
        rows, failures = [], []
        total = len(self.paths)
        for position, path in enumerate(self.paths, start=1):
            if self._cancel_requested:
                break
            self.status.emit(f"Analyzing {position} of {total} — {path.name}")
            try:
                rows.append(analyze_file(path))
            except Exception:
                failures.append(path.name)
            self.progress.emit(round(position / total * 100))
        self.finished.emit(rows, failures, self._cancel_requested)
