from pathlib import Path
import re

from config import OUTPUT_DIR_FILE

DEFAULT_OUTPUT_DIR = Path.cwd() / "output"


def _load_output_dir() -> Path:
    """Read output_dir.txt if present; otherwise return default path."""
    cfg_path = Path(__file__).with_name(OUTPUT_DIR_FILE)
    if cfg_path.exists():
        try:
            stored = cfg_path.read_text(encoding="utf-8").strip()
            if stored:
                candidate = Path(stored)
                if candidate.exists() and candidate.is_dir():
                    return candidate
        except OSError:
            pass
    return DEFAULT_OUTPUT_DIR


MEDIA_DIR = str(_load_output_dir())


def sanitize_filename(title):
    # Remove invalid filename characters and trim
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    # Remove non-ASCII characters
    title = re.sub(r'[^\x00-\x7F]+', '', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Limit filename length (e.g., 100 chars)
    return title[:100]
