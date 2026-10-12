"""Instagram reel and post downloads.

Public posts only - no authentication. Instagram titles are generic ("Video by
someuser"), so files are named by timestamp instead; two reels from one account
would otherwise overwrite each other.
"""

import os
from datetime import datetime

import yt_dlp

from downloader import DownloadCancelled, DownloadFailed, _base_opts, download_and_convert
from file_utils import MEDIA_DIR, sanitize_filename
from logs import logger

# yt-dlp's own message here is a paragraph long and tells a GUI user to pass
# --cookies-from-browser, which they cannot do.
_LOGIN_HINT = (
    "This Instagram post may be private, deleted, invalid, or require sign-in. "
    "Only publicly accessible posts and reels can be downloaded."
)
_LOGIN_MARKERS = ("login required", "empty media response", "rate-limit", "log in")


def _friendly(error):
    text = str(error)
    if any(m in text.lower() for m in _LOGIN_MARKERS):
        return _LOGIN_HINT
    return text


def _stamp(fmt, index=None):
    """Reel-Audio-20260803-131500[-2] — the name the file gets."""
    kind = "Audio" if fmt == "mp3" else "Video"
    when = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{index}" if index else ""
    return f"Reel-{kind}-{when}{suffix}"


def download_instagram(url, fmt, quality, target_dir=None, progress_callback=None,
                       status_callback=None, is_cancelled=None, retry_items=None):
    """Download one Instagram post. Returns (filenames, [skipped descriptions]).

    A carousel post holds several items; each video lands in a subfolder named
    after the post. Image-only slides carry no formats and are reported skipped.
    """
    base_dir = target_dir if target_dir else MEDIA_DIR
    os.makedirs(base_dir, exist_ok=True)

    # noplaylist stays off: a carousel must come back as a playlist so every
    # item is visible, rather than yt-dlp silently picking one.
    if is_cancelled and is_cancelled():
        raise DownloadCancelled()
    opts = {**_base_opts(is_cancelled=is_cancelled), "skip_download": True, "noplaylist": False}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error("Instagram extract failed", extra={"url": url, "error": str(e)})
        raise Exception(_friendly(e)) from e

    entries = [e for e in (info.get("entries") or []) if e] if info.get("_type") == "playlist" else None
    if entries and retry_items:
        retry_urls = set(retry_items)
        entries = [entry for entry in entries if (entry.get("webpage_url") or entry.get("url") or url) in retry_urls]
        if not entries:
            raise RuntimeError("The skipped Instagram items are no longer available")

    if not entries:
        name = _stamp(fmt)
        filename = download_and_convert(
            url, fmt, quality, target_dir=base_dir,
            progress_callback=progress_callback,
            status_callback=(
                lambda stage, name: status_callback(stage, 1, 1, name)
            ) if status_callback else None,
            is_cancelled=is_cancelled,
            title=name,
        )
        logger.info("Instagram post saved", extra={"url": url, "file": filename})
        return [filename], []

    post_dir = os.path.join(base_dir, sanitize_filename(f"Instagram-{info.get('id') or 'post'}"))
    os.makedirs(post_dir, exist_ok=True)

    done, skipped = [], []
    total = len(entries)
    for idx, entry in enumerate(entries, start=1):
        if is_cancelled and is_cancelled():
            pending = [entry.get("webpage_url") or entry.get("url") or url for entry in entries[idx - 1:]]
            raise DownloadCancelled(done, skipped + pending)
        entry_url = entry.get("webpage_url") or entry.get("url") or url
        try:
            # Index every carousel file: a post can save several within the same
            # second, and the timestamp alone would collide.
            filename = download_and_convert(
                entry_url, fmt, quality, target_dir=post_dir, title=_stamp(fmt, idx),
                progress_callback=progress_callback,
                status_callback=(
                    lambda stage, name, item=idx: status_callback(stage, item, total, name)
                ) if status_callback else None,
                is_cancelled=is_cancelled,
            )
            done.append(filename)
        except DownloadCancelled:
            pending = [entry.get("webpage_url") or entry.get("url") or url for entry in entries[idx - 1:]]
            raise DownloadCancelled(done, skipped + pending)
        except Exception as e:
            logger.warning("Instagram item skipped", extra={"url": entry_url, "error": str(e)})
            skipped.append(entry_url)
        if progress_callback:
            progress_callback(int(idx / total * 100))

    if not done:
        raise DownloadFailed(
            _friendly(f"No downloadable video found in this post ({total} items)"),
            skipped, skipped,
        )

    logger.info(
        "Instagram post saved",
        extra={"url": url, "saved": len(done), "skipped": len(skipped), "dir": post_dir},
    )
    return done, skipped
