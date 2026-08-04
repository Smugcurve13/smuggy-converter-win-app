from pathlib import Path
import tempfile

from PySide6.QtCore import QThread, Signal

import updater


class UpdateCheckWorker(QThread):
    """Asks GitHub whether a newer release exists. Silent unless one does."""
    found = Signal(dict)  # {"version", "url", "size", "notes_url"}

    def run(self):
        info = updater.check()  # never raises; logs and returns None on failure
        if info:
            self.found.emit(info)


class UpdateDownloadWorker(QThread):
    """Streams the release zip to a temp file."""
    progress = Signal(int)  # 0-100, same convention as DownloadWorker
    finished = Signal(bool, str)  # success, zip path or error message

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        dest = Path(tempfile.gettempdir()) / "smuggy-update.zip"
        try:
            ok = updater.download(
                self.url,
                dest,
                progress_callback=self.progress.emit,
                is_cancelled=lambda: self._cancel,
            )
        except Exception as e:
            updater.logger.error("Update download failed", extra={"error": str(e)})
            dest.unlink(missing_ok=True)
            self.finished.emit(False, str(e))
            return
        # A cancel is not a failure, and the dialog is already gone.
        self.finished.emit(ok, str(dest) if ok else "")
