import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import downloader


class PlaylistDuplicateTests(unittest.TestCase):
    def test_playlist_archive_is_scoped_to_title_format_and_quality(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            archive = downloader.playlist_archive_path(target, "My Mix", "mp3", 320)

        self.assertEqual(
            archive,
            target / "My Mix" / ".smuggyconverter-mp3-320.archive",
        )

    def test_existing_archive_warns_before_reselecting_playlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            archive = downloader.playlist_archive_path(target, "My Mix", "mp3", 320)
            archive.parent.mkdir()
            archive.write_text("youtube abc123\n", encoding="utf-8")

            self.assertTrue(downloader.has_playlist_archive(target, "My Mix", "mp3", 320))

    def test_archived_items_are_reported_as_already_downloaded_not_saved_again(self):
        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, _url, download=False):
                return {"title": "One"} if not download else None

        with tempfile.TemporaryDirectory() as target:
            with mock.patch.object(downloader.yt_dlp, "YoutubeDL", FakeYDL):
                done, failed, skipped = downloader.download_selected(
                    "Mix", {"One": "https://example.test/one"}, "mp3", 320, target_dir=target
                )

        self.assertEqual(done, [])
        self.assertEqual(failed, [])
        self.assertEqual(skipped, ["One"])


if __name__ == "__main__":
    unittest.main()
