import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

import gui.converter_window as converter_window


class _Worker:
    def __init__(self):
        self.cancelled = False

    def isRunning(self):
        return True

    def cancel(self):
        self.cancelled = True


class WindowProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_active_convert_button_cancels_and_status_is_shown(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}):
                window = converter_window.ConverterWindow()

            worker = _Worker()
            window.worker = worker
            window._start_loading(show_progress=True)
            self.assertEqual(window.convert_btn.text(), "Cancel")
            self.assertTrue(window.convert_btn.isEnabled())

            window._on_convert_clicked()
            self.assertTrue(worker.cancelled)
            self.assertEqual(window.convert_btn.text(), "Cancelling…")
            self.assertFalse(window.convert_btn.isEnabled())

            window._on_download_status("Downloading 1 of 2 — Track")
            self.assertEqual(window.progress_bar.format(), "Downloading 1 of 2 — Track")
            self.assertEqual(window.version_label.text(), f"v{converter_window.__version__}")
            window.close()

    def test_analyze_music_opens_with_the_selected_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}), \
                 patch.object(converter_window, "MusicAnalysisDialog") as dialog_class:
                dialog = dialog_class.return_value
                window = converter_window.ConverterWindow()
                window._open_music_analysis()

            dialog_class.assert_called_once_with(Path(tmp), window)
            dialog.exec.assert_called_once()
            window.close()


if __name__ == "__main__":
    unittest.main()
