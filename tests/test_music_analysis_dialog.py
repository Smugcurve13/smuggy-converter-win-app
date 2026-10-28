import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from gui.music_analysis_dialog import MusicAnalysisDialog


class _RunningWorker:
    def __init__(self):
        self.cancelled = False

    def isRunning(self):
        return True

    def cancel(self):
        self.cancelled = True


class MusicAnalysisDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_results_show_bpm_key_and_camelot_and_allow_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = MusicAnalysisDialog(Path(tmp))
            dialog._show_results([
                {"file": "Track.mp3", "bpm": 128.2, "key": "A minor", "camelot": "8A", "key_confidence": 0.22, "path": "/music/Track.mp3"}
            ], [], False)

            self.assertEqual(dialog.results_table.rowCount(), 1)
            self.assertEqual(dialog.results_table.item(0, 1).text(), "128.2")
            self.assertEqual(dialog.results_table.item(0, 2).text(), "A minor")
            self.assertEqual(dialog.results_table.item(0, 3).text(), "8A")
            self.assertTrue(dialog.export_button.isEnabled())
            dialog.close()

    def test_close_while_running_cancels_without_destroying_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            dialog = MusicAnalysisDialog(Path(tmp))
            dialog.worker = _RunningWorker()

            dialog.reject()

            self.assertTrue(dialog.worker.cancelled)
            dialog.worker = None


if __name__ == "__main__":
    unittest.main()
