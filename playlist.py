import datetime

import yt_dlp

from logs import logger

# Playlist metadata only. Everything that downloads lives in downloader.py.


def extract_playlist_info(url):
    """Return (playlist_title, [[url, title, duration], ...])."""
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
        "logger": logger,
    }
    final_array = []
    playlist_title = "playlist"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        playlist_title = info.get("title", playlist_title)
        for entry in info.get("entries", []):
            if not entry or "id" not in entry:
                continue
            duration = entry.get("duration") or 0
            final_array.append([
                f"https://www.youtube.com/watch?v={entry['id']}",
                entry.get("title", "Unknown"),
                str(datetime.timedelta(seconds=duration)),
            ])
        logger.info("Playlist entries fetched", extra={"count": len(final_array)})
        return playlist_title, final_array
    except Exception as e:
        logger.error("Failed to extract playlist", extra={"url": url, "error": str(e)})
        return None, []


def extract_video_info_from_array(final_array):
    """[[url, title, duration], ...] -> {title: url}"""
    return {row[1]: row[0] for row in final_array}
