"""Safe local audio trimming through the bundled FFmpeg."""

from __future__ import annotations

import subprocess
from pathlib import Path

from config import FFMPEG_PATH


def default_trimmed_path(source: Path) -> Path:
    """Return an unused sibling path without ever replacing the source."""
    source = Path(source)
    stem = f"{source.stem} (trimmed)"
    candidate = source.with_name(f"{stem}.mp3")
    count = 2
    while candidate.exists():
        candidate = source.with_name(f"{source.stem} (trimmed {count}).mp3")
        count += 1
    return candidate


def trim_audio(source: Path, start_seconds: float, end_seconds: float, destination: Path | None = None) -> Path:
    """Trim one audio file accurately enough for normal playback and keep its original."""
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")
    if start_seconds < 0 or end_seconds <= start_seconds:
        raise ValueError("The end time must be after the start time.")

    destination = Path(destination) if destination else default_trimmed_path(source)
    if destination == source:
        raise ValueError("Choose a new output file; the original audio is kept unchanged.")
    if destination.exists():
        raise FileExistsError(f"Output file already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.stem}.smuggy-trim{destination.suffix}")
    command = [
        FFMPEG_PATH, "-y", "-v", "error", "-i", str(source),
        "-ss", f"{start_seconds:.3f}", "-to", f"{end_seconds:.3f}",
        "-map", "0:a:0", "-vn", "-map_metadata", "0",
        "-c:a", "libmp3lame", "-q:a", "2", str(temporary),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        temporary.replace(destination)
    except subprocess.CalledProcessError as exc:
        temporary.unlink(missing_ok=True)
        raise ValueError(exc.stderr.strip() or "FFmpeg could not trim this audio file.") from exc
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination
