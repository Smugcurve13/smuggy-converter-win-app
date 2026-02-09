import sys
import platform
from pathlib import Path

from logs import logger


class FFmpegNotFoundError(Exception):
    pass


def _base_path() -> Path:
    """
    Returns the correct base directory depending on whether
    the app is running from source or a PyInstaller bundle.
    """
    if getattr(sys, "frozen", False):
        # Running inside PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running from source
        return Path(__file__).resolve().parent.parent


def get_ffmpeg_dir() -> Path:
    """
    Returns the directory containing ffmpeg binaries.
    """
    base = _base_path()

    if platform.system() == "Windows":
        ffmpeg_dir = base / "ffmpeg"
    else:
        logger.error("ffmpeg resolver called on unsupported platform: %s", platform.system())
        raise RuntimeError("This resolver is currently Windows-only.")

    if not ffmpeg_dir.exists():
        logger.error("Bundled ffmpeg directory not found at: %s", ffmpeg_dir)
        raise FFmpegNotFoundError(f"Bundled ffmpeg directory not found at: {ffmpeg_dir}")

    return ffmpeg_dir


def get_ffmpeg_path() -> Path:
    """
    Returns the absolute path to ffmpeg.exe
    """
    ffmpeg_dir = get_ffmpeg_dir()
    ffmpeg_path = ffmpeg_dir / "ffmpeg.exe"

    if not ffmpeg_path.exists():
        logger.error("ffmpeg.exe not found at: %s", ffmpeg_path)
        raise FFmpegNotFoundError(f"ffmpeg.exe not found at: {ffmpeg_path}")

    return ffmpeg_path


def get_ffprobe_path() -> Path:
    """
    Returns the absolute path to ffprobe.exe
    """
    ffmpeg_dir = get_ffmpeg_dir()
    ffprobe_path = ffmpeg_dir / "ffprobe.exe"

    if not ffprobe_path.exists():
        logger.error("ffprobe.exe not found at: %s", ffprobe_path)
        raise FFmpegNotFoundError(f"ffprobe.exe not found at: {ffprobe_path}")

    return ffprobe_path
