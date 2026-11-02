from pathlib import Path
import unittest

import release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_v140_notes_render_with_the_same_categories_used_in_app(self):
        notes = release_notes.get_notes("1.4.0")
        rendered = release_notes.render_markdown("1.4.0")

        self.assertEqual(set(notes), {"NEW", "CHANGED", "FIXED"})
        for category, entries in notes.items():
            self.assertIn(f"## {category.title()}", rendered)
            for entry in entries:
                self.assertIn(entry, rendered)
        self.assertIn("Mix/radio", rendered)
        self.assertIn("Getting Started and What's New", rendered)

    def test_v150_notes_include_bpm_playlist_and_log_changes(self):
        notes = release_notes.get_notes("1.5.0")

        self.assertTrue(any("BPM" in entry for entry in notes["NEW"]))
        self.assertTrue(any("crop" in entry.lower() for entry in notes["NEW"]))
        self.assertTrue(any("already downloaded" in entry.lower() for entry in notes["FIXED"]))
        self.assertTrue(any("log" in entry.lower() for entry in notes["CHANGED"]))


        rendered = release_notes.render_markdown("1.5.0-alpha.1")

        self.assertIn("Analyze Music", rendered)
        self.assertIn("BPM", rendered)
        self.assertIn("macOS", rendered)

    def test_ffmpeg_notice_includes_its_gpl_and_source_reference(self):
        root = Path(__file__).parents[1]
        notice = (root / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

        self.assertTrue((root / "licenses" / "FFmpeg-GPL-3.0.txt").is_file())
        self.assertIn("FFmpeg-GPL-3.0.txt", notice)
        self.assertIn("894da5ca7d", notice)

    def test_missing_notes_render_as_empty(self):
        self.assertEqual(release_notes.render_markdown("9.9.9"), "")


if __name__ == "__main__":
    unittest.main()
