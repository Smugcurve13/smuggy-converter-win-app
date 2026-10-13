import unittest
from pathlib import Path
from unittest.mock import patch

import downloader


class ProgressCancellationTests(unittest.TestCase):
    def test_download_hook_stops_at_the_next_progress_event_when_cancelled(self):
        progress = []
        hook = downloader._progress_hook(progress.append, is_cancelled=lambda: True)

        with self.assertRaises(downloader.DownloadCancelled):
            hook({"status": "downloading", "total_bytes": 100, "downloaded_bytes": 25})
        self.assertEqual(progress, [])

    def test_postprocessor_hook_reports_conversion_without_cancelling(self):
        stages = []
        hook = downloader._postprocessor_hook(lambda stage: stages.append(stage))

        hook({"status": "started"})
        self.assertEqual(stages, ["Converting"])

    def test_playlist_stops_before_the_next_item_after_cancellation(self):
        cancelled = [False]
        calls = []

        def fake_download(_url, _fmt, _quality, **kwargs):
            calls.append(kwargs["title"])
            cancelled[0] = True
            return f"{kwargs['title']}.mp3"

        with patch.object(downloader, "download_and_convert", side_effect=fake_download):
            with self.assertRaises(downloader.DownloadCancelled) as caught:
                downloader.download_selected(
                    "Mix", {"One": "one", "Two": "two"}, "mp3", 320,
                    is_cancelled=lambda: cancelled[0],
                )

        self.assertEqual(calls, ["One"])
        self.assertEqual(caught.exception.saved, ["One.mp3"])

    def test_worker_reports_cancellation_with_saved_count(self):
        import core.download_worker as worker_module

        worker = worker_module.DownloadWorker(
            "yt playlist", "", "mp3", 320, Path("."),
            selected_videos=[["one", "One", "1:00"]], playlist_title="Mix",
        )
        emitted = []
        worker.finished.connect(lambda *args: emitted.append(args))
        with patch.object(
            worker_module, "download_selected", side_effect=downloader.DownloadCancelled(["One.mp3"], [["one", "One", "1:00"]])
        ):
            worker.run()

        self.assertEqual(emitted, [(False, "Cancelled — 1 saved", "Mix")])
        self.assertEqual(worker.result["retry_items"], [["one", "One", "1:00"]])

    def test_worker_reports_partial_playlist_result_with_retry_subset(self):
        import core.download_worker as worker_module

        selected = [["one", "One", "1:00"], ["two", "Two", "1:00"]]
        worker = worker_module.DownloadWorker(
            "yt playlist", "", "mp3", 320, Path("."), selected_videos=selected, playlist_title="Mix",
        )
        with patch.object(worker_module, "download_selected", return_value=(["One.mp3"], [("Two", "two")])):
            worker.run()

        self.assertEqual(worker.result["state"], "Completed with issues")
        self.assertEqual(worker.result["retry_items"], [["two", "Two", "1:00"]])

    def test_worker_keeps_retry_subset_when_every_playlist_item_fails(self):
        import core.download_worker as worker_module

        selected = [["one", "One", "1:00"], ["two", "Two", "1:00"]]
        worker = worker_module.DownloadWorker(
            "yt playlist", "", "mp3", 320, Path("."), selected_videos=selected, playlist_title="Mix",
        )
        with patch.object(worker_module, "download_selected", return_value=([], [("One", "one"), ("Two", "two")])):
            worker.run()

        self.assertEqual(worker.result["state"], "Failed")
        self.assertEqual(worker.result["retry_items"], selected)

    def test_worker_keeps_spotify_remainder_after_cancellation(self):
        import core.download_worker as worker_module

        tracks = [{"track": "One", "artists": "A"}, {"track": "Two", "artists": "B"}]
        worker = worker_module.DownloadWorker("spotify", "", "mp3", 320, Path("."), csv_path="tracks.csv")
        with patch.object(worker_module, "read_exportify_csv", return_value=tracks), patch.object(
            worker_module, "download_spotify_csv", side_effect=downloader.DownloadCancelled(["One - A.mp3"], [tracks[1]])
        ):
            worker.run()

        self.assertEqual(worker.result["state"], "Cancelled")
        self.assertEqual(worker.result["retry_items"], [tracks[1]])

    def test_worker_keeps_skipped_instagram_items_for_retry(self):
        import core.download_worker as worker_module

        worker = worker_module.DownloadWorker("instagram", "post", "mp4", 1080, Path("."))
        with patch.object(worker_module, "download_instagram", return_value=(["one.mp4"], ["https://instagram.test/two"])):
            worker.run()

        self.assertEqual(worker.result["state"], "Completed with issues")
        self.assertEqual(worker.result["retry_items"], ["https://instagram.test/two"])

    def test_worker_keeps_all_failed_instagram_items_for_retry(self):
        import core.download_worker as worker_module

        skipped = ["https://instagram.test/one", "https://instagram.test/two"]
        worker = worker_module.DownloadWorker("instagram", "post", "mp4", 1080, Path("."))
        with patch.object(worker_module, "download_instagram", side_effect=downloader.DownloadFailed("No video", skipped, skipped)):
            worker.run()

        self.assertEqual(worker.result["state"], "Failed")
        self.assertEqual(worker.result["retry_items"], skipped)

    def test_worker_keeps_cancelled_single_instagram_url_for_retry(self):
        import core.download_worker as worker_module

        worker = worker_module.DownloadWorker("instagram", "https://instagram.test/reel", "mp4", 1080, Path("."))
        with patch.object(
            worker_module, "download_instagram", side_effect=downloader.DownloadCancelled([], [worker.url])
        ):
            worker.run()

        self.assertEqual(worker.result["state"], "Cancelled")
        self.assertEqual(worker.result["retry_items"], [worker.url])

    def test_worker_retries_only_failed_duplicate_spotify_rows(self):
        import core.download_worker as worker_module

        first = {"track": "Same", "artists": "Artist", "id": "first"}
        second = {"track": "Same", "artists": "Artist", "id": "second"}
        worker = worker_module.DownloadWorker("spotify", "", "mp3", 320, Path("."), csv_path="tracks.csv")
        with patch.object(worker_module, "read_exportify_csv", return_value=[first, second]), patch.object(
            worker_module, "download_spotify_csv", return_value=(["Same - Artist.mp3"], [second])
        ):
            worker.run()

        self.assertEqual(worker.result["retry_items"], [second])


if __name__ == "__main__":
    unittest.main()
