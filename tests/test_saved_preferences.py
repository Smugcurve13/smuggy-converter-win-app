import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
import gui.converter_window as converter_window


class SettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
    def test_migrates_existing_output_folder_into_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp)
            output_dir = app_dir / "downloads"
            output_dir.mkdir()
            old_file = app_dir / "output_dir.txt"
            old_file.write_text(str(output_dir), encoding="utf-8")
            settings_file = app_dir / "settings.json"

            with patch.multiple(
                config,
                APP_DATA_DIR=app_dir,
                output_dir_file=old_file,
                settings_file=settings_file,
                _legacy_output_dir_file=app_dir / "missing-output_dir.txt",
            ):
                settings = config.load_settings()

            self.assertEqual(settings["output_folder"], str(output_dir))
            self.assertEqual(
                json.loads(settings_file.read_text(encoding="utf-8"))["output_folder"],
                str(output_dir),
            )
            self.assertEqual(old_file.read_text(encoding="utf-8"), str(output_dir))

    def test_round_trips_all_preferences_in_one_document(self):
        preferences = {
            "mode": "instagram",
            "format": "mp4",
            "audio_quality": 256,
            "video_quality": 1080,
            "output_folder": "/chosen/output",
            "remember_url": True,
            "url": "https://www.instagram.com/reel/example/",
            "onboarding_completed": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            app_dir = Path(tmp)
            with patch.multiple(
                config,
                APP_DATA_DIR=app_dir,
                output_dir_file=app_dir / "output_dir.txt",
                settings_file=app_dir / "settings.json",
                _legacy_output_dir_file=app_dir / "legacy-output_dir.txt",
            ):
                config.save_settings(preferences)
                loaded = config.load_settings()

        self.assertEqual(loaded, preferences)

    def test_window_restores_separate_audio_and_video_qualities(self):
        with tempfile.TemporaryDirectory() as tmp:
            preferences = {
                "mode": "instagram",
                "format": "mp4",
                "audio_quality": 192,
                "video_quality": 720,
                "output_folder": tmp,
            }
            with patch.object(converter_window, "load_settings", return_value=preferences):
                window = converter_window.ConverterWindow()

            self.assertEqual(window._current_mode(), "instagram")
            self.assertEqual(window._current_format(), "mp4")
            self.assertEqual(window.quality_combo.currentData(), 720)
            self.assertEqual(window.output_dir, Path(tmp))

            window.format_combo.setCurrentIndex(0)
            self.assertEqual(window.quality_combo.currentData(), 192)
            window.close()

    def test_saves_changes_and_removes_url_when_opt_out_is_disabled(self):
        saved = []
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(
                converter_window, "load_settings", return_value={"output_folder": tmp}
            ), patch.object(
                converter_window, "save_settings", side_effect=lambda settings: saved.append(dict(settings))
            ):
                window = converter_window.ConverterWindow()
                next(button for button in window.mode_group.buttons() if button.text() == "YT Playlist").click()
                window.format_combo.setCurrentIndex(1)
                window.quality_combo.setCurrentIndex(window.quality_combo.findData(720))
                window.remember_url_checkbox.setChecked(True)
                window.url_input.setText("https://example.com/video")
                window.remember_url_checkbox.setChecked(False)

            self.assertEqual(saved[-1]["mode"], "yt playlist")
            self.assertEqual(saved[-1]["format"], "mp4")
            self.assertEqual(saved[-1]["video_quality"], 720)
            self.assertFalse(saved[-1]["remember_url"])
            self.assertNotIn("url", saved[-1])
            window.close()


if __name__ == "__main__":
    unittest.main()
