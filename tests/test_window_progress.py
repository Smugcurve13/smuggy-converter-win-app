import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_trim_audio_opens_with_the_selected_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}), \
                 patch("gui.converter_window.AudioTrimDialog") as dialog_class:
                dialog = dialog_class.return_value
                window = converter_window.ConverterWindow()
                window._open_audio_trim()

            dialog_class.assert_called_once_with(Path(tmp), window)
            dialog.exec.assert_called_once()
            window.close()

    def test_video_crop_is_visible_for_mp4_and_log_button_opens_current_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}), \
                 patch.object(converter_window.platform, "system", return_value="Linux"), \
                 patch.object(converter_window.subprocess, "Popen") as popen:
                window = converter_window.ConverterWindow()
                window.format_combo.setCurrentIndex(1)

                self.assertFalse(window.crop_label.isHidden())
                self.assertFalse(window.crop_combo.isHidden())
                self.assertEqual(window.open_log_btn.text(), "Open Log")
                window._open_log()

            popen.assert_called_once_with(["xdg-open", str(converter_window.current_log_path)])
            window.close()

    def test_whats_new_button_does_not_close_update_prompt(self):
        with patch.object(converter_window, "_open_notes") as open_notes, patch.object(
            converter_window.QMessageBox, "done"
        ) as close_dialog:
            box = converter_window._UpdateMessageBox("https://example.test/notes")
            notes_button = box.addButton("What's New", converter_window.QMessageBox.ActionRole)
            box.notes_button = notes_button
            with patch.object(box, "clickedButton", return_value=notes_button):
                box.done(0)

        close_dialog.assert_not_called()
        open_notes.assert_called_once_with("https://example.test/notes")
        box.hide()
        box.deleteLater()

    def test_instagram_retry_preserves_the_selected_crop(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}), \
                 patch.object(converter_window, "DownloadWorker") as worker_class:
                next_worker = MagicMock()
                worker_class.return_value = next_worker
                window = converter_window.ConverterWindow()
                window.worker = MagicMock(
                    mode="instagram", url="https://instagram.test/reel", fmt="mp4", quality=1080,
                    crop="9:16 (Reel)", csv_path=None, playlist_title=None,
                )

                window._retry_failed_tracks({"retry_items": ["https://instagram.test/reel"]})

            self.assertEqual(worker_class.call_args.kwargs["crop"], "9:16 (Reel)")
            window.close()


if __name__ == "__main__":
    unittest.main()
