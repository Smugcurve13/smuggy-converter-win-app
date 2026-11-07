import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audio_trim import default_trimmed_path, trim_audio


class AudioTrimTests(unittest.TestCase):
    def test_default_trimmed_path_keeps_original_and_avoids_collisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Track.mp3"
            source.write_bytes(b"original")
            first = default_trimmed_path(source)
            first.write_bytes(b"first trim")

            self.assertEqual(first.name, "Track (trimmed).mp3")
            self.assertEqual(default_trimmed_path(source).name, "Track (trimmed 2).mp3")
            self.assertEqual(source.read_bytes(), b"original")

    def test_trim_audio_writes_through_a_temporary_mp3_then_replaces_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Track.mp3"
            destination = Path(tmp) / "Track (trimmed).mp3"
            source.write_bytes(b"original")

            def fake_run(command, check, capture_output, text):
                temporary = Path(command[-1])
                self.assertEqual(Path(command[0]).name, "ffmpeg")
                self.assertEqual(command[1], "-y")
                self.assertIn("-ss", command)
                self.assertIn("-to", command)
                self.assertIn("-c:a", command)
                self.assertEqual(command[command.index("-c:a") + 1], "libmp3lame")
                self.assertEqual(temporary.suffix, ".mp3")
                temporary.write_bytes(b"trimmed")

            with patch("audio_trim.subprocess.run", side_effect=fake_run):
                saved = trim_audio(source, 1.25, 4.5, destination)

            self.assertEqual(saved, destination)
            self.assertEqual(destination.read_bytes(), b"trimmed")
            self.assertEqual(source.read_bytes(), b"original")
            self.assertFalse((Path(tmp) / "Track (trimmed).smuggy-trim.mp3").exists())

    def test_trim_audio_rejects_an_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Track.mp3"
            destination = Path(tmp) / "Track (trimmed).mp3"
            source.write_bytes(b"original")
            destination.write_bytes(b"saved trim")

            with patch("audio_trim.subprocess.run") as run, self.assertRaisesRegex(FileExistsError, "already exists"):
                trim_audio(source, 1, 4, destination)

            run.assert_not_called()
            self.assertEqual(destination.read_bytes(), b"saved trim")

    def test_trim_audio_rejects_an_empty_or_reversed_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Track.mp3"
            source.write_bytes(b"original")

            with self.assertRaisesRegex(ValueError, "after the start"):
                trim_audio(source, 5, 5)


if __name__ == "__main__":
    unittest.main()
