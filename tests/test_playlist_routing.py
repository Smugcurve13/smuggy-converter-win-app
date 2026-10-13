import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

import gui.converter_window as converter_window


class _AcceptedDialog:
    def __init__(self, *_args):
        self.selected_videos = [["https://www.youtube.com/watch?v=one", "One", "1:00"]]

    def exec(self):
        return converter_window.QDialog.Accepted


class _Worker:
    def __init__(self, *_args, **_kwargs):
        self.progress = type("Signal", (), {"connect": lambda *_: None})()
        self.status = type("Signal", (), {"connect": lambda *_: None})()
        self.finished = type("Signal", (), {"connect": lambda *_: None})()

    def start(self):
        pass


class PlaylistRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_list_only_youtube_urls_are_playlist_urls(self):
        self.assertTrue(converter_window._is_youtube_playlist_url("https://www.youtube.com/watch?list=PLexample"))
        self.assertTrue(converter_window._is_youtube_playlist_url("https://www.youtube.com/playlist?list=PLexample"))

    def test_single_video_mix_is_not_routed_to_playlist_mode(self):
        self.assertFalse(converter_window._is_youtube_playlist_url("https://www.youtube.com/watch?v=qYcoJpqCha4&list=RDqYcoJpqCha4"))

    def test_non_youtube_url_is_not_routed_to_playlist_mode(self):
        self.assertFalse(converter_window._is_youtube_playlist_url("https://notyoutube.com/watch?list=PLexample"))

    def test_list_only_url_switches_to_playlist_mode_and_extracts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            converter_window, "load_settings", return_value={"output_folder": tmp}
        ), patch.object(converter_window.QTimer, "singleShot"), patch.object(
            converter_window, "extract_playlist_info", return_value=("Mix", [["one", "One", "1:00"]])
        ) as extract, patch.object(converter_window, "PlaylistSelectionDialog", _AcceptedDialog), patch.object(
            converter_window, "DownloadWorker", _Worker
        ):
            window = converter_window.ConverterWindow()
            window.url_input.setText("https://www.youtube.com/watch?list=PLexample")
            window._on_convert_clicked()

        self.assertEqual(window._current_mode(), "yt playlist")
        extract.assert_called_once_with("https://www.youtube.com/watch?list=PLexample")
        window.close()


if __name__ == "__main__":
    unittest.main()
