import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

import downloader
import gui.converter_window as converter_window


class _Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _YDL:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        return {
            "title": "A video",
            "thumbnail": "https://i.ytimg.com/vi/example/maxresdefault.jpg",
        }


class YouTubeThumbnailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_thumbnail_mode_hides_media_controls(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            converter_window, "load_settings", return_value={"output_folder": tmp}
        ):
            window = converter_window.ConverterWindow()
            next(button for button in window.mode_group.buttons() if button.text() == "YT Thumbnail").click()

        self.assertEqual(window.url_label.text(), "YouTube Video or Playlist URL:")
        self.assertTrue(window.format_combo.isHidden())
        self.assertTrue(window.quality_combo.isHidden())
        self.assertTrue(window.crop_combo.isHidden())
        self.assertEqual(window.convert_btn.text(), "Download Thumbnail(s)")
        window.close()

    def test_playlist_url_starts_one_thumbnail_worker_for_every_available_video(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            converter_window, "load_settings", return_value={"output_folder": tmp}
        ), patch.object(
            converter_window, "extract_playlist_info", return_value=("Mix", [["one", "One", "1:00"]])
        ), patch.object(converter_window, "DownloadWorker") as worker_class:
            worker = MagicMock()
            worker_class.return_value = worker
            window = converter_window.ConverterWindow()
            next(button for button in window.mode_group.buttons() if button.text() == "YT Thumbnail").click()
            window.url_input.setText("https://www.youtube.com/playlist?list=PLexample")
            window._on_convert_clicked()

        self.assertEqual(worker_class.call_args.args[:5], ("yt thumbnail playlist", "https://www.youtube.com/playlist?list=PLexample", "thumbnail", None, window.output_dir))
        self.assertEqual(worker_class.call_args.kwargs["selected_videos"], [["one", "One", "1:00"]])
        self.assertEqual(worker_class.call_args.kwargs["playlist_title"], "Mix")
        worker.start.assert_called_once()
        window.close()

    def test_single_thumbnail_uses_yt_dlp_metadata_and_saves_the_image(self):
        progress = []
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(downloader.yt_dlp, "YoutubeDL", _YDL), \
             patch.object(downloader, "urlopen", return_value=_Response(b"jpeg-bytes")) as urlopen:
            saved = downloader.download_thumbnail(
                "https://www.youtube.com/watch?v=example", tmp, progress_callback=progress.append
            )

            self.assertEqual(saved, "A video.jpg")
            self.assertEqual((Path(tmp) / saved).read_bytes(), b"jpeg-bytes")
            self.assertEqual(progress[-1], 100)
            self.assertEqual(urlopen.call_args.args[0].full_url, "https://i.ytimg.com/vi/example/maxresdefault.jpg")

    def test_playlist_thumbnails_keep_duplicate_titles_distinct(self):
        calls = []

        def fake_download(url, target_dir, title=None, **kwargs):
            calls.append((url, title, target_dir))
            return f"{title}.jpg"

        with tempfile.TemporaryDirectory() as tmp, patch.object(
            downloader, "download_thumbnail", side_effect=fake_download
        ):
            saved, failed = downloader.download_selected_thumbnails(
                "Mix", [("Same", "https://youtube.test/1"), ("Same", "https://youtube.test/2")], tmp
            )

        self.assertEqual(saved, ["Same.jpg", "Same (2).jpg"])
        self.assertEqual(failed, [])
        self.assertEqual([title for _, title, _ in calls], ["Same", "Same (2)"])

    def test_playlist_thumbnails_keep_a_duplicate_suffix_after_title_truncation(self):
        title = "a" * 100
        calls = []

        def fake_download(url, target_dir, title=None, **kwargs):
            calls.append(title)
            return f"{title}.jpg"

        with patch.object(downloader, "download_thumbnail", side_effect=fake_download):
            downloader.download_selected_thumbnails("Mix", [(title, "one"), (title, "two")])

        self.assertNotEqual(calls[0], calls[1])
        self.assertEqual(calls[1][-4:], " (2)")
        self.assertLessEqual(len(calls[1]), 100)

    def test_thumbnail_retry_does_not_overwrite_an_earlier_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            playlist_dir = Path(tmp) / "Mix"
            playlist_dir.mkdir()
            (playlist_dir / "Same.jpg").write_bytes(b"saved first thumbnail")
            with patch.object(downloader, "download_thumbnail", return_value="Same (2).jpg") as download:
                downloader.download_selected_thumbnails("Mix", [("Same", "two")], tmp)

            self.assertEqual(download.call_args.kwargs["title"], "Same (2)")
            self.assertEqual((playlist_dir / "Same.jpg").read_bytes(), b"saved first thumbnail")


if __name__ == "__main__":
    unittest.main()
