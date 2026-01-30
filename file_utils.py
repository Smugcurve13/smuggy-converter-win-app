import os
import uuid
import json
import asyncio
from datetime import datetime, timedelta

MEDIA_DIR = "media"
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