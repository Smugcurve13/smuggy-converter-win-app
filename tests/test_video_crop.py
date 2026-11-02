import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_crop import crop_filter


class VideoCropTests(unittest.TestCase):
    def test_original_does_not_add_a_filter(self):
        self.assertIsNone(crop_filter("Original"))

    def test_reel_crop_is_a_centered_nine_by_sixteen_filter(self):
        self.assertEqual(
            crop_filter("9:16 (Reel)"),
            "crop=min(iw\\,ih*9/16):min(ih\\,iw*16/9):(iw-ow)/2:(ih-oh)/2",
        )

    def test_unknown_crop_is_rejected(self):
        with self.assertRaises(ValueError):
            crop_filter("CinemaScope")


if __name__ == "__main__":
    unittest.main()
