import unittest

from gui.converter_window import _normalise_youtube_single_url


class YouTubeUrlHandlingTests(unittest.TestCase):
    def test_single_video_mix_url_becomes_canonical_video_url(self):
        url = "https://www.youtube.com/watch?v=qYcoJpqCha4&list=RDqYcoJpqCha4&start_radio=1"

        self.assertEqual(
            _normalise_youtube_single_url(url),
            "https://www.youtube.com/watch?v=qYcoJpqCha4",
        )

    def test_short_youtube_mix_url_becomes_canonical_video_url(self):
        self.assertEqual(
            _normalise_youtube_single_url("https://youtu.be/qYcoJpqCha4?list=RDqYcoJpqCha4&start_radio=1"),
            "https://www.youtube.com/watch?v=qYcoJpqCha4",
        )

    def test_supported_youtube_path_urls_become_canonical_video_urls(self):
        for path in ("shorts/qYcoJpqCha4", "live/qYcoJpqCha4", "embed/qYcoJpqCha4"):
            with self.subTest(path=path):
                self.assertEqual(
                    _normalise_youtube_single_url(f"https://www.youtube.com/{path}?list=RDqYcoJpqCha4&start_radio=1"),
                    "https://www.youtube.com/watch?v=qYcoJpqCha4",
                )

    def test_radio_url_without_a_video_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Malformed URL"):
            _normalise_youtube_single_url("https://www.youtube.com/watch?start_radio=1")

    def test_playlist_without_a_video_id_is_left_for_playlist_mode(self):
        url = "https://www.youtube.com/watch?list=PLexample"
        self.assertEqual(_normalise_youtube_single_url(url), url)

    def test_lookalike_host_is_not_treated_as_youtube(self):
        url = "https://notyoutube.com/watch?list=PLexample"
        self.assertEqual(_normalise_youtube_single_url(url), url)


if __name__ == "__main__":
    unittest.main()
