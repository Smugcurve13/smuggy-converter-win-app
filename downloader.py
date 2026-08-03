import os

import yt_dlp

from config import FFMPEG_DIR
from file_utils import sanitize_filename, MEDIA_DIR
from logs import logger


def _progress_hook(callback):
    """Translate yt-dlp's byte counts into a 0-100 percentage."""
    def hook(d):
        if d.get("status") != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if total:
            # ponytail: mp4 pulls video then audio, so this sweeps 0-100 twice.
            # Fine for a progress bar; weight by stream size if it ever matters.
            callback(min(100, int(d.get("downloaded_bytes", 0) / total * 100)))
    return hook


def _base_opts(progress_callback=None, throttle=False):
    opts = {
        "noplaylist": True,
        "quiet": True,
        "ignoreerrors": False,
        "logger": logger,
        "ffmpeg_location": FFMPEG_DIR,
    }
    if throttle:
        # Back-to-back requests earn "HTTP Error 403: Forbidden" partway through a
        # batch. yt-dlp's randomised pause between downloads avoids that.
        opts["sleep_interval"] = 1
        opts["max_sleep_interval"] = 4
    if progress_callback:
        opts["progress_hooks"] = [_progress_hook(progress_callback)]
    return opts


def _format_opts(fmt, quality, source_metadata=True):
    """Format-specific yt-dlp options. Conversion is left to yt-dlp's postprocessors.

    source_metadata=False omits the tagging/thumbnail postprocessors. Callers that
    supply their own authoritative tags (Spotify) should pass False — otherwise
    the source's title, description, lyrics and thumbnail get written first and
    have to be scrubbed back out.
    """
    if fmt == "mp3":
        opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": str(quality or 320),
                },
            ],
        }
        if source_metadata:
            opts["writethumbnail"] = True  # EmbedThumbnail needs this; yt-dlp cleans up after
            opts["postprocessors"] += [
                {"key": "FFmpegMetadata"},  # title/artist/album/date, whatever the extractor has
                {"key": "EmbedThumbnail"},  # cover art
            ]
        return opts
    if fmt == "mp4":
        h = quality or 1080
        # Remux, not re-encode: seconds instead of minutes.
        #
        # H.264 is only worth asking for at 1080p and below - YouTube ships none
        # above that. Asking anyway is actively harmful: an avc1 tier matches at
        # ANY height under the cap, so a 1080p H.264 stream beats a 2160p AV1 one
        # and "4K" silently yields 1080p.
        #
        # Above 1080p, take the best resolution and let yt-dlp's default codec
        # order apply - it already ranks av01 over vp9, and AV1 is the one that
        # belongs in an MP4 container. Resolution outranks codec in the default
        # sort, so no custom format_sort is needed (and a custom one would hurt:
        # "vcodec:h264" flattens the rest and lets VP9 beat AV1).
        prefer_h264 = (
            f"bestvideo[height<={h}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
            if h <= 1080 else ""
        )
        return {
            "format": (
                f"{prefer_h264}"
                # AAC explicitly: left alone yt-dlp picks Opus, the same
                # MP4-container playback problem AV1 has.
                f"bestvideo[height<={h}]+bestaudio[acodec^=mp4a]/"
                f"bestvideo[height<={h}]+bestaudio/"
                f"best[height<={h}]"
            ),
            "merge_output_format": "mp4",
            "postprocessors": [{"key": "FFmpegMetadata"}] if source_metadata else [],
        }
    raise ValueError(f"Invalid format: {fmt}")


def download_and_convert(url, fmt, quality, target_dir=None, progress_callback=None, title=None,
                         source_metadata=True, throttle=False):
    """Download one URL and produce a single {title}.{fmt} file. The only downloader.

    `url` may be any yt-dlp input, including a search like "ytsearch1:some query".
    Pass `title` to name the file yourself and skip the info round-trip - callers
    that already know the track name (e.g. Spotify) should.
    """
    logger.info("Starting download", extra={"url": url, "fmt": fmt, "quality": quality})
    base_dir = target_dir if target_dir else MEDIA_DIR
    os.makedirs(base_dir, exist_ok=True)

    opts = _base_opts(progress_callback, throttle)
    try:
        if title is None:
            with yt_dlp.YoutubeDL({**opts, "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title", "downloaded_file")
            logger.info("Fetched info", extra={"title": title, "ext": info.get("ext")})

        # An all-non-ASCII title sanitizes to "", which would yield a bare ".mp3".
        safe_title = sanitize_filename(title) or "download"
        filename = f"{safe_title}.{fmt}"
        opts.update(_format_opts(fmt, quality, source_metadata))
        # Postprocessors decide the final extension; %(ext)s lets them.
        opts["outtmpl"] = os.path.join(base_dir, f"{safe_title}.%(ext)s")

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(url, download=True)

        logger.info("Conversion complete", extra={"path": os.path.join(base_dir, filename)})
        return filename
    except Exception as e:
        logger.error("Download/convert failed", extra={"url": url, "error": str(e)})
        raise


def download_selected(playlist_title, videos_dict, fmt, quality, target_dir=None,
                      progress_callback=None):
    """Download the picked videos into a playlist subfolder. Progress ticks per video."""
    base_dir = target_dir if target_dir else MEDIA_DIR
    playlist_dir = os.path.join(base_dir, sanitize_filename(playlist_title))
    os.makedirs(playlist_dir, exist_ok=True)

    results = []
    total = len(videos_dict)
    for idx, url in enumerate(videos_dict.values()):
        results.append(download_and_convert(url, fmt, quality, target_dir=playlist_dir,
                                            throttle=True))
        if progress_callback:
            progress_callback(int((idx + 1) / total * 100) if total else 100)
    logger.info("Playlist complete", extra={"playlist": playlist_title, "count": len(results)})
    return results
