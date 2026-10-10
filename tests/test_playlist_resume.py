import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import downloader


class PlaylistResumeTests(unittest.TestCase):
    def test_downloader_retries_and_resumes_network_transfers(self):
        opts = downloader._base_opts()

        self.assertEqual(opts["retries"], 10)
        self.assertEqual(opts["fragment_retries"], 10)
        self.assertEqual(opts["extractor_retries"], 3)
        self.assertEqual(opts["file_access_retries"], 3)
        self.assertTrue(opts["continuedl"])
        self.assertTrue(opts["overwrites"])

    def test_unarchived_existing_output_is_replaced(self):
        with tempfile.TemporaryDirectory() as target:
            stale = os.path.join(target, "Same title.mp3")
            open(stale, "wb").close()

            with downloader.yt_dlp.YoutubeDL(downloader._base_opts()) as ydl:  # type: ignore[arg-type]
                self.assertIsNone(ydl.existing_file([stale], default_overwrite=False))

            self.assertFalse(os.path.exists(stale))

    def test_existing_file_does_not_bypass_url_archive(self):
        downloads = []

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download=False):
                downloads.append(download)
                return {"title": "Already Done", "ext": "webm"}

        with tempfile.TemporaryDirectory() as target:
            open(os.path.join(target, "Already Done.mp3"), "wb").close()
            with mock.patch.object(downloader.yt_dlp, "YoutubeDL", FakeYDL):
                result = downloader.download_and_convert("https://example.test/video", "mp3", 320,
                                                         target_dir=target)

        self.assertEqual(result, "Already Done.mp3")
        self.assertEqual(downloads, [False, True])

    def test_playlist_continues_after_one_item_fails(self):
        archives = []

        def fake_download(url, fmt, quality, **kwargs):
            archives.append(kwargs["download_archive"])
            if url == "bad":
                raise RuntimeError("temporary DNS failure")
            return f"{kwargs['title']}.mp3"

        with tempfile.TemporaryDirectory() as target:
            with mock.patch.object(downloader, "download_and_convert", side_effect=fake_download) as call:
                done, failed = downloader.download_selected(
                    "Mix", {"One": "one", "Two": "bad", "Three": "three"},
                    "mp3", 320, target_dir=target,
                )

        self.assertEqual(done, ["One.mp3", "Three.mp3"])
        self.assertEqual(failed, ["Two"])
        self.assertEqual(call.call_count, 3)
        self.assertEqual([c.kwargs["title"] for c in call.call_args_list], ["One", "Two", "Three"])
        self.assertEqual(len(set(archives)), 1)
        self.assertTrue(archives[0].endswith(".smuggyconverter-mp3-320.archive"))


class PlaylistWorkerTests(unittest.TestCase):
    def test_partial_playlist_failure_is_reported(self):
        import types

        class BoundSignal:
            def __init__(self):
                self.callbacks = []

            def connect(self, callback):
                self.callbacks.append(callback)

            def emit(self, *args):
                for callback in self.callbacks:
                    callback(*args)

        class Signal:
            def __set_name__(self, owner, name):
                self.name = name

            def __get__(self, instance, owner):
                if instance is None:
                    return self
                return instance.__dict__.setdefault(self.name, BoundSignal())

        qtcore = types.ModuleType("PySide6.QtCore")
        setattr(qtcore, "QThread", type("QThread", (), {"__init__": lambda self: None}))
        setattr(qtcore, "Signal", lambda *args: Signal())
        pyside = types.ModuleType("PySide6")
        setattr(pyside, "QtCore", qtcore)
        spotify = types.ModuleType("spotify")
        setattr(spotify, "download_spotify_csv", lambda *args, **kwargs: ([], []))
        instagram = types.ModuleType("instagram")
        setattr(instagram, "download_instagram", lambda *args, **kwargs: ([], []))

        modules = {
            "PySide6": pyside, "PySide6.QtCore": qtcore,
            "spotify": spotify, "instagram": instagram,
        }
        with mock.patch.dict(sys.modules, modules):
            sys.modules.pop("core.download_worker", None)
            from core import download_worker

            cases = [
                ((["One.mp3"], ["Two"]),
                 (True, "1 tracks saved, 1 failed: Two", "Mix")),
                (([], ["One", "Two"]),
                 (False, "No tracks could be downloaded (2 failed)", "")),
            ]
            for result, expected in cases:
                worker = download_worker.DownloadWorker(
                    "yt playlist", "", "mp3", 320, Path("."),
                    selected_videos=[["one", "One", "1:00"], ["two", "Two", "1:00"]],
                    playlist_title="Mix",
                )
                emitted = []
                worker.finished.connect(lambda *args: emitted.append(args))

                with mock.patch.object(download_worker, "download_selected", return_value=result):
                    worker.run()

                self.assertEqual(emitted, [expected])


if __name__ == "__main__":
    unittest.main()
