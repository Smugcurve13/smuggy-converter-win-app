import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

import playlist
from gui.playlist_selection_dialog import PlaylistSelectionDialog


class _FakeYDL:
    def __init__(self, _opts, result):
        self.result = result

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def extract_info(self, _url, download=False):
        return self.result


class PlaylistAvailabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_keeps_explicitly_unavailable_entries_with_a_reason(self):
        result = {
            "title": "Mix",
            "entries": [
                {"id": "available", "title": "Available", "duration": 61},
                {"id": "private", "title": "[Private video]", "availability": "private"},
                {"id": "deleted", "title": "[Deleted video]", "availability": "unavailable"},
            ],
        }
        with patch.object(playlist.yt_dlp, "YoutubeDL", lambda opts: _FakeYDL(opts, result)):
            title, rows = playlist.extract_playlist_info("https://www.youtube.com/playlist?list=x")

        self.assertEqual(title, "Mix")
        self.assertEqual(rows[0], ["https://www.youtube.com/watch?v=available", "Available", "0:01:01"])
        self.assertEqual(rows[1][-1], "Private")
        self.assertEqual(rows[2][-1], "Deleted")

    def test_dialog_disables_unavailable_rows_and_ignores_them_in_select_all(self):
        dialog = PlaylistSelectionDialog(
            "Mix",
            [
                ["https://www.youtube.com/watch?v=available", "Available", "0:01:01"],
                ["", "[Private video]", "0:00:00", "Private"],
            ],
        )

        unavailable = dialog.video_list.item(1)
        self.assertFalse(unavailable.flags() & Qt.ItemIsEnabled)
        self.assertEqual(unavailable.checkState(), Qt.Unchecked)

        dialog._toggle_select_all(True)
        self.assertEqual(dialog.video_list.item(0).checkState(), Qt.Checked)
        self.assertEqual(unavailable.checkState(), Qt.Unchecked)
        dialog.close()

    def test_search_handles_unavailable_rows(self):
        dialog = PlaylistSelectionDialog("Mix", [["one", "One", "1:00"], ["", "[Private video]", "0:00:00", "Private"]])
        dialog.search_input.setText("one")
        self.assertFalse(dialog.video_list.item(0).isHidden())
        self.assertTrue(dialog.video_list.item(1).isHidden())
        dialog.close()


if __name__ == "__main__":
    unittest.main()
