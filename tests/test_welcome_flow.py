import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QLabel

from gui.welcome_dialog import WelcomeDialog
import gui.converter_window as converter_window


class WelcomeFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_first_launch_dialog_includes_getting_started_and_current_notes(self):
        dialog = WelcomeDialog("1.4.0", onboarding=True)
        text = "\n".join(label.text() for label in dialog.findChildren(QLabel))

        self.assertIn("Getting Started", text)
        self.assertIn("What's New in v1.4.0", text)
        self.assertIn("Start Using SmuggyConverter", dialog.continue_button.text())
        dialog.close()

    def test_update_dialog_shows_notes_without_repeating_onboarding(self):
        dialog = WelcomeDialog("1.4.0", onboarding=False)
        text = "\n".join(label.text() for label in dialog.findChildren(QLabel))

        self.assertNotIn("Getting Started", text)
        self.assertIn("What's New in v1.4.0", text)
        self.assertEqual(dialog.continue_button.text(), "Continue")
        dialog.close()

    def test_startup_marks_onboarding_complete_once_after_acceptance(self):
        shown = []

        class FakeDialog:
            def __init__(self, version, onboarding, parent):
                shown.append((version, onboarding))

            def exec(self):
                return converter_window.QDialog.Accepted

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(converter_window, "load_settings", return_value={"output_folder": tmp}), patch.object(
                converter_window, "save_settings"
            ), patch.object(converter_window, "WelcomeDialog", FakeDialog):
                window = converter_window.ConverterWindow()
                window._show_startup_notes()
                window._show_startup_notes()

        self.assertEqual(shown, [(converter_window.__version__, True)])
        self.assertTrue(window.settings["onboarding_completed"])
        self.assertEqual(window.settings["last_seen_version"], converter_window.__version__)
        window.close()


if __name__ == "__main__":
    unittest.main()
