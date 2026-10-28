import csv
import math
import os
import tempfile
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from music_analysis import (
    DECODE_TIMEOUT_SECONDS,
    MAX_ANALYSIS_SECONDS,
    _decode,
    _estimate_bpm,
    _estimate_key,
    camelot_key,
    analyze_file,
    audio_files,
    export_csv,
)
from core.music_analysis_worker import MusicAnalysisWorker

import numpy as np


RATE = 44_100


def _click_track(bpm=120, seconds=12):
    samples = np.zeros(RATE * seconds, dtype=np.float32)
    interval = 60 / bpm
    click_size = int(RATE * 0.018)
    click = np.hanning(click_size).astype(np.float32)
    for start in range(0, len(samples), int(RATE * interval)):
        end = min(start + click_size, len(samples))
        samples[start:end] += click[:end - start]
    return samples


def _a_minor(seconds=8):
    timeline = np.arange(RATE * seconds, dtype=np.float32) / RATE
    return sum(np.sin(2 * math.pi * hz * timeline) for hz in (220.0, 261.6256, 329.6276)).astype(np.float32)


class MusicAnalysisTests(unittest.TestCase):
    def test_estimates_a_120_bpm_click_track(self):
        self.assertAlmostEqual(_estimate_bpm(_click_track(), RATE), 120, delta=2)

    def test_identifies_an_a_minor_chord_and_camelot_key(self):
        key, scale, confidence = _estimate_key(_a_minor(), RATE)
        self.assertEqual((key, scale), ("A", "minor"))
        self.assertGreater(confidence, 0)
        self.assertEqual(camelot_key(key, scale), "8A")

    def test_decode_limits_duration_and_process_time(self):
        completed = SimpleNamespace(returncode=0, stdout=np.zeros(8, dtype="<f4").tobytes(), stderr=b"")
        with patch("music_analysis.subprocess.run", return_value=completed) as run:
            _decode(Path("long-mix.mp3"))

        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-t") + 1], str(MAX_ANALYSIS_SECONDS))
        self.assertEqual(run.call_args.kwargs["timeout"], DECODE_TIMEOUT_SECONDS)

    def test_analyze_file_decodes_audio_with_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clicks.wav"
            samples = (_click_track() * 0.8 * 32767).astype("<i2")
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(RATE)
                output.writeframes(samples.tobytes())

            result = analyze_file(path)

        self.assertEqual(result["file"], "clicks.wav")
        self.assertAlmostEqual(result["bpm"], 120, delta=2)
        self.assertEqual(result["camelot"], "")

    def test_worker_reports_each_file_and_continues_after_a_decode_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clicks.wav"
            samples = (_click_track() * 0.8 * 32767).astype("<i2")
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(RATE)
                output.writeframes(samples.tobytes())

            worker = MusicAnalysisWorker([path, Path(tmp) / "missing.mp3"])
            statuses, results = [], []
            worker.status.connect(statuses.append)
            worker.finished.connect(lambda rows, failures, cancelled: results.append((rows, failures, cancelled)))
            worker.run()

        self.assertEqual(statuses, ["Analyzing 1 of 2 — clicks.wav", "Analyzing 2 of 2 — missing.mp3"])
        rows, failures, cancelled = results[0]
        self.assertEqual([row["file"] for row in rows], ["clicks.wav"])
        self.assertEqual(failures, ["missing.mp3"])
        self.assertFalse(cancelled)

    def test_audio_file_discovery_and_csv_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "Track.MP3").touch()
            (folder / "notes.txt").touch()
            self.assertEqual([path.name for path in audio_files(folder)], ["Track.MP3"])

            csv_path = export_csv([
                {"file": "=HYPERLINK(\"https://example.invalid\")", "bpm": 128.0, "key": "A minor", "camelot": "8A", "key_confidence": 0.2, "path": str(folder / "Track.MP3")},
                {"file": "\t=1+1", "bpm": 0.0, "key": "\r@SUM(1,1)", "camelot": "", "key_confidence": 0.0, "path": "  -unsafe"},
            ], folder / "analysis.csv")
            text = csv_path.read_text(encoding="utf-8")
            with csv_path.open(newline="", encoding="utf-8") as source:
                exported = list(csv.DictReader(source))

        self.assertIn("file,bpm,key,camelot,key_confidence,path", text)
        self.assertIn("'=HYPERLINK", text)
        self.assertEqual(exported[1]["file"], "'\t=1+1")
        self.assertEqual(exported[1]["key"], "'\r@SUM(1,1)")
        self.assertEqual(exported[1]["path"], "'  -unsafe")


if __name__ == "__main__":
    unittest.main()
