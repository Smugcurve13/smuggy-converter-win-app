import unittest
from unittest.mock import patch

import instagram
from downloader import DownloadCancelled


class _FakeYDL:
    def __init__(self, _opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def extract_info(self, _url, download=False):
        return {"id": "post"}


class InstagramCancellationTests(unittest.TestCase):
    def test_single_post_cancellation_keeps_source_url_for_retry(self):
        url = "https://www.instagram.com/reel/example/"
        with patch.object(instagram.yt_dlp, "YoutubeDL", _FakeYDL), patch.object(
            instagram, "download_and_convert", side_effect=DownloadCancelled()
        ):
            with self.assertRaises(DownloadCancelled) as caught:
                instagram.download_instagram(url, "mp4", 1080)

        self.assertEqual(caught.exception.retry_items, [url])


if __name__ == "__main__":
    unittest.main()
