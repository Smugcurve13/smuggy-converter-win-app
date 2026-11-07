import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from gui.audio_trim_dialog import AudioTrimDialog


class AudioTrimDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_audio_file_and_valid_range_enable_trim_to_a_new_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Track.mp3"
            source.write_bytes(b"audio")
            dialog = AudioTrimDialog(Path(tmp))

            self.assertFalse(dialog.trim_button.isEnabled())
            dialog._set_source(source)
            dialog.start_input.setValue(1.25)
            dialog.end_input.setValue(4.5)

            self.assertTrue(dialog.trim_button.isEnabled())
            self.assertEqual(Path(dialog.output_input.text()).name, "Track (trimmed).mp3")
            dialog.close()

    def test_trim_starts_a_background_worker_with_the_selected_range(self):
        with tempfile.TemporaryDirectory() as tmp, patch("gui.audio_trim_dialog.AudioTrimWorker") as worker_class:
            source = Path(tmp) / "Track.mp3"
            source.write_bytes(b"audio")
            worker = MagicMock()
            worker_class.return_value = worker
            dialog = AudioTrimDialog(Path(tmp))
            dialog._set_source(source)
            dialog.end_input.setValue(3)

            dialog._start()

            self.assertEqual(worker_class.call_args.args[:4], (source, 0.0, 3.0, Path(dialog.output_input.text())))
            worker.start.assert_called_once()
            self.assertEqual(dialog.trim_button.text(), "Trimming audio…")
            dialog.worker = None
            dialog.close()


if __name__ == "__main__":
    unittest.main()
