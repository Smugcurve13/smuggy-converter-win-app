"""Local BPM and musical-key estimates for audio files."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import numpy as np

from config import FFMPEG_PATH

SAMPLE_RATE = 44_100
MAX_ANALYSIS_SECONDS = 120
DECODE_TIMEOUT_SECONDS = 30
_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus"}
_PITCHES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_CAMELOT = {
    ("A", "minor"): "8A", ("A#", "minor"): "3A", ("B", "minor"): "10A",
    ("C", "minor"): "5A", ("C#", "minor"): "12A", ("D", "minor"): "7A",
    ("D#", "minor"): "2A", ("E", "minor"): "9A", ("F", "minor"): "4A",
    ("F#", "minor"): "11A", ("G", "minor"): "6A", ("G#", "minor"): "1A",
    ("A", "major"): "11B", ("A#", "major"): "6B", ("B", "major"): "1B",
    ("C", "major"): "8B", ("C#", "major"): "3B", ("D", "major"): "10B",
    ("D#", "major"): "5B", ("E", "major"): "12B", ("F", "major"): "7B",
    ("F#", "major"): "2B", ("G", "major"): "9B", ("G#", "major"): "4B",
}
_MAJOR_PROFILE = np.array((6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88))
_MINOR_PROFILE = np.array((6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17))


def audio_files(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in _AUDIO_SUFFIXES)


def camelot_key(key: str, scale: str) -> str:
    return _CAMELOT.get((key, scale), "")


def _decode(path: Path) -> np.ndarray:
    command = [
        FFMPEG_PATH, "-v", "error", "-i", str(path), "-t", str(MAX_ANALYSIS_SECONDS), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "f32le", "pipe:1",
    ]
    result = subprocess.run(command, capture_output=True, check=False, timeout=DECODE_TIMEOUT_SECONDS)
    if result.returncode or not result.stdout:
        detail = result.stderr.decode("utf-8", "replace").strip() or "FFmpeg could not decode this file."
        raise ValueError(detail)
    return np.frombuffer(result.stdout, dtype="<f4").copy()


def _estimate_bpm(samples: np.ndarray, sample_rate: int) -> float:
    """Estimate tempo from positive short-time energy changes."""
    hop = 512
    frame = 1024
    if len(samples) < frame * 4:
        return 0.0
    frames = np.lib.stride_tricks.sliding_window_view(samples, frame)[::hop]
    energy = np.sqrt(np.mean(frames * frames, axis=1))
    onset = np.maximum(0, np.diff(energy, prepend=energy[0]))
    onset -= onset.mean()
    if not np.any(onset > 0):
        return 0.0
    size = 1 << (len(onset) * 2 - 1).bit_length()
    spectrum = np.fft.rfft(onset, size)
    correlation = np.fft.irfft(spectrum * spectrum.conjugate(), size)[:len(onset)]
    minimum_lag = max(1, round((60 * sample_rate) / (200 * hop)))
    maximum_lag = min(len(correlation) - 1, round((60 * sample_rate) / (60 * hop)))
    if maximum_lag <= minimum_lag:
        return 0.0
    lag = minimum_lag + int(np.argmax(correlation[minimum_lag:maximum_lag + 1]))
    return round((60 * sample_rate) / (lag * hop), 1)


def _estimate_key(samples: np.ndarray, sample_rate: int) -> tuple[str, str, float]:
    """Estimate the best-fitting major/minor key from an averaged chroma vector."""
    frame = 4096
    hop = 2048
    if len(samples) < frame:
        return "", "", 0.0
    frames = np.lib.stride_tricks.sliding_window_view(samples, frame)[::hop]
    windowed = frames * np.hanning(frame)
    power = np.abs(np.fft.rfft(windowed, axis=1)) ** 2
    frequencies = np.fft.rfftfreq(frame, 1 / sample_rate)
    usable = (frequencies >= 55) & (frequencies <= 5_000)
    frequencies = frequencies[usable]
    midi = np.rint(69 + 12 * np.log2(frequencies / 440)).astype(int) % 12
    chroma = np.zeros(12)
    np.add.at(chroma, midi, power[:, usable].sum(axis=0))
    if not chroma.any():
        return "", "", 0.0
    chroma = (chroma - chroma.mean()) / (chroma.std() or 1)
    candidates = []
    for scale, profile in (("major", _MAJOR_PROFILE), ("minor", _MINOR_PROFILE)):
        normalized = (profile - profile.mean()) / profile.std()
        for root, pitch in enumerate(_PITCHES):
            candidates.append((float(np.dot(chroma, np.roll(normalized, root)) / 12), pitch, scale))
    candidates.sort(reverse=True)
    score, key, scale = candidates[0]
    confidence = max(0.0, score - candidates[1][0])
    return key, scale, round(confidence, 3)


def analyze_file(path: Path) -> dict[str, str | float]:
    samples = _decode(Path(path))
    bpm = _estimate_bpm(samples, SAMPLE_RATE)
    key, scale, confidence = _estimate_key(samples, SAMPLE_RATE)
    if confidence < 0.07:
        key = scale = ""
    return {
        "file": Path(path).name,
        "path": str(path),
        "bpm": bpm,
        "key": f"{key} {scale}".strip(),
        "camelot": camelot_key(key, scale),
        "key_confidence": confidence,
    }


def _csv_value(value: str | float) -> str | float:
    if isinstance(value, str):
        first = next((char for char in value if not (char.isspace() or ord(char) < 32)), "")
        if first in {"=", "+", "-", "@"}:
            return "'" + value
    return value


def export_csv(rows: list[dict[str, str | float]], destination: Path) -> Path:
    fields = ("file", "bpm", "key", "camelot", "key_confidence", "path")
    with Path(destination).open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{field: _csv_value(row.get(field, "")) for field in fields} for row in rows])
    return Path(destination)
