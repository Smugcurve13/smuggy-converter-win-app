import os
import uuid
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
METADATA_EXT = ".metadata.json"


def ensure_media_dir():
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)


def generate_uuid_filename(ext):
    return f"{uuid.uuid4()}.{ext}"


def get_media_path(file_id):
    return os.path.join(MEDIA_DIR, file_id)


def cleanup_file(filepath):
    try:
        os.remove(filepath)
    except Exception:
        pass

def sanitize_filename(title):
    # Remove invalid filename characters and trim
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    # Remove non-ASCII characters
    title = re.sub(r'[^\x00-\x7F]+', '', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Limit filename length (e.g., 100 chars)
    return title[:100]