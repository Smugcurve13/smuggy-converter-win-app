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

    def test_missing_notes_render_as_empty(self):
        self.assertEqual(release_notes.render_markdown("9.9.9"), "")


if __name__ == "__main__":
    unittest.main()
