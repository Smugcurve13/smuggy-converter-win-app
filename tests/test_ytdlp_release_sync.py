import tempfile
import unittest
from pathlib import Path

from scripts.sync_ytdlp_release import apply_release, has_newer_release


class YtdlpReleaseSyncTests(unittest.TestCase):
    def test_apply_release_updates_core_and_increments_only_the_patch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("yt-dlp==2026.8.19\n", encoding="utf-8")
            (root / "version.py").write_text('__version__ = "1.5.2"\n', encoding="utf-8")
            (root / "release_notes.py").write_text(
                'NOTES = {\n    "1.5.2": {"NEW": []},\n}\n', encoding="utf-8"
            )

            version = apply_release(root, "2026.10.26")

            self.assertEqual(version, "1.5.3")
            self.assertEqual((root / "requirements.txt").read_text(encoding="utf-8"), "yt-dlp==2026.10.26\n")
            self.assertEqual((root / "version.py").read_text(encoding="utf-8"), '__version__ = "1.5.3"\n')
            self.assertIn('"1.5.3": {\n        "NEW": [],\n        "CHANGED": [\n            "Updated yt-dlp core to v2026.10.26.",', (root / "release_notes.py").read_text(encoding="utf-8"))

    def test_has_newer_release_compares_numeric_version_parts(self):
        self.assertTrue(has_newer_release("2026.10.26", "2026.8.19"))
        self.assertFalse(has_newer_release("2026.8.19", "2026.8.19"))
        self.assertFalse(has_newer_release("2026.8.9", "2026.8.19"))


if __name__ == "__main__":
    unittest.main()
