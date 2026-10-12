import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

import instagram
import gui.converter_window as converter_window


class ContextualGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_spotify_help_is_automatic_once_and_manual_afterward(self):
        with tempfile.TemporaryDirectory() as tmp:
            saved = []
            with patch.object(
                converter_window, "load_settings", return_value={"output_folder": tmp}
            ), patch.object(
                converter_window, "save_settings", side_effect=lambda settings: saved.append(dict(settings))
            ):
                window = converter_window.ConverterWindow()
                shown = []
                window._show_spotify_help = lambda: shown.append(True)
                spotify = next(button for button in window.mode_group.buttons() if button.text() == "Spotify")
                youtube = next(button for button in window.mode_group.buttons() if button.text() == "YT Video")
                spotify.click()
                youtube.click()
                spotify.click()

            self.assertEqual(shown, [True])
            self.assertTrue(saved[-1]["spotify_help_shown"])
            self.assertFalse(window.spotify_help_btn.isHidden())
            window.close()

    def test_instagram_private_or_missing_media_has_public_access_guidance(self):
        message = instagram._friendly(Exception("login required: empty media response"))

        self.assertIn("private", message.lower())
        self.assertIn("deleted", message.lower())
        self.assertIn("public", message.lower())


if __name__ == "__main__":
    unittest.main()
