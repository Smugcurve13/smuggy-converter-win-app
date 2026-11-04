import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

import yt_dlp
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor

from config import FFMPEG_DIR
from file_utils import sanitize_filename, MEDIA_DIR
from logs import logger
from video_crop import crop_filter


class DownloadCancelled(Exception):
    def __init__(self, saved=None, retry_items=None):
        super().__init__("Cancelled")
        self.saved = saved or []
        self.retry_items = retry_items or []


class DownloadFailed(Exception):
    def __init__(self, message, failed=(), retry_items=()):
        super().__init__(message)
        self.failed = list(failed)
        self.retry_items = list(retry_items)


class CenterCropPostProcessor(FFmpegPostProcessor):
    """Apply one centered crop after yt-dlp has produced the MP4."""

    def __init__(self, downloader=None, crop="Original"):
        super().__init__(downloader)
        self.filter = crop_filter(crop)

    def run(self, information):
        if not self.filter:
            return [], information
        source = Path(information["filepath"])
        temporary = source.with_name(f"{source.stem}.smuggy-crop{source.suffix}")
        self.run_ffmpeg(str(source), str(temporary), ["-vf", self.filter, "-c:a", "copy"])
        temporary.replace(source)
        return [], information


def playlist_archive_path(target_dir, playlist_title, fmt, quality) -> Path:
    playlist_dir = Path(target_dir) / (sanitize_filename(playlist_title) or "playlist")
    return playlist_dir / f".smuggyconverter-{fmt}-{quality or 'best'}.archive"


def has_playlist_archive(target_dir, playlist_title, fmt, quality) -> bool:
    return playlist_archive_path(target_dir, playlist_title, fmt, quality).is_file()


def _youtube_video_id(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/").split("/", 1)[0]
    return parse_qs(parsed.query).get("v", [""])[0]


def _archive_contains_url(archive: Path, url: str) -> bool:
    video_id = _youtube_video_id(url)
    if not video_id or not archive.is_file():
        return False
    try:
        return any(line.rstrip().endswith(f" {video_id}") for line in archive.read_text(encoding="utf-8").splitlines())
    except OSError:
        return False


def _progress_hook(callback=None, is_cancelled=None):
    """Translate yt-dlp's byte counts into a 0-100 percentage."""
    def hook(d):
        if is_cancelled and is_cancelled():
            raise DownloadCancelled()
        if d.get("status") != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if total and callback:
            # ponytail: mp4 pulls video then audio, so this sweeps 0-100 twice.
            # Fine for a progress bar; weight by stream size if it ever matters.
            callback(min(100, int(d.get("downloaded_bytes", 0) / total * 100)))
    return hook


def _postprocessor_hook(stage_callback):
    def hook(d):
        if d.get("status") == "started":
            stage_callback("Converting")
    return hook


def _base_opts(progress_callback=None, throttle=False, is_cancelled=None, stage_callback=None):
    opts = {
        "noplaylist": True,
        "quiet": True,
        "ignoreerrors": False,
        "logger": logger,
        "ffmpeg_location": FFMPEG_DIR,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "file_access_retries": 3,
        "continuedl": True,
        "overwrites": True,
    }
    if throttle:
        # Back-to-back requests earn "HTTP Error 403: Forbidden" partway through a
        # batch. yt-dlp's randomised pause between downloads avoids that.
        opts["sleep_interval"] = 1
        opts["max_sleep_interval"] = 4
    if progress_callback or is_cancelled:
        opts["progress_hooks"] = [_progress_hook(progress_callback, is_cancelled)]
    if stage_callback:
        opts["postprocessor_hooks"] = [_postprocessor_hook(stage_callback)]
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


def _thumbnail_suffix(url: str) -> str:
    suffix = Path(urlsplit(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _distinct_output_title(title: str, count: int) -> str:
    """Keep a duplicate suffix inside sanitize_filename's 100-character limit."""
    base = sanitize_filename(title) or "download"
    suffix = "" if count == 1 else f" ({count})"
    return f"{base[:100 - len(suffix)].rstrip()}{suffix}"


def download_thumbnail(url, target_dir=None, progress_callback=None, status_callback=None,
                       is_cancelled=None, title=None):
    """Save the source's best thumbnail without downloading its media."""
    if is_cancelled and is_cancelled():
        raise DownloadCancelled()
    base_dir = Path(target_dir or MEDIA_DIR)
    base_dir.mkdir(parents=True, exist_ok=True)
    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        info = ydl.extract_info(url, download=False)
    thumbnail_url = info.get("thumbnail")
    if not thumbnail_url:
        raise RuntimeError("YouTube did not provide a thumbnail for this video")
    title = title or info.get("title", "thumbnail")
    safe_title = sanitize_filename(title) or "thumbnail"
    filename = f"{safe_title}{_thumbnail_suffix(thumbnail_url)}"
    destination = base_dir / filename
    temporary = destination.with_suffix(destination.suffix + ".part")
    if status_callback:
        status_callback("Downloading", title)
    request = Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request) as response, temporary.open("wb") as output:
            total = int(response.headers.get("Content-Length", 0) or 0)
            saved = 0
            while chunk := response.read(64 * 1024):
                if is_cancelled and is_cancelled():
                    raise DownloadCancelled()
                output.write(chunk)
                saved += len(chunk)
                if total and progress_callback:
                    progress_callback(min(100, int(saved / total * 100)))
        temporary.replace(destination)
    except DownloadCancelled:
        temporary.unlink(missing_ok=True)
        raise
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    if progress_callback:
        progress_callback(100)
    logger.info("Thumbnail saved", extra={"url": url, "path": str(destination)})
    return filename


def download_selected_thumbnails(playlist_title, videos, target_dir=None, progress_callback=None,
                                 status_callback=None, is_cancelled=None):
    """Download every selected playlist thumbnail into its playlist folder."""
    playlist_dir = Path(target_dir or MEDIA_DIR) / (sanitize_filename(playlist_title) or "playlist")
    playlist_dir.mkdir(parents=True, exist_ok=True)
    done, failed, used_titles = [], [], {}
    items = list(videos)
    total = len(items)
    for index, (title, url) in enumerate(items, start=1):
        if is_cancelled and is_cancelled():
            raise DownloadCancelled(done, failed + items[index - 1:])
        key = (sanitize_filename(title) or "thumbnail").casefold()
        count = used_titles.get(key, 0)
        while True:
            count += 1
            output_title = _distinct_output_title(title, count)
            if not any(playlist_dir.glob(f"{output_title}.*")):
                break
        used_titles[key] = count
        try:
            saved = download_thumbnail(
                url, playlist_dir, title=output_title, is_cancelled=is_cancelled,
                progress_callback=progress_callback,
                status_callback=(
                    lambda stage, name, item=index: status_callback(stage, item, total, name)
                ) if status_callback else None,
            )
            done.append(saved)
        except DownloadCancelled:
            raise DownloadCancelled(done, failed + items[index - 1:])
        except Exception as exc:
            logger.error("Playlist thumbnail failed", extra={"title": title, "url": url, "error": str(exc)})
            failed.append((title, url))
        if progress_callback:
            progress_callback(int(index / total * 100) if total else 100)
    return done, failed


def download_and_convert(url, fmt, quality, target_dir=None, progress_callback=None, status_callback=None,
                         is_cancelled=None, title=None, source_metadata=True, throttle=False,
                         download_archive=None, crop="Original"):
    """Download one URL and produce a single {title}.{fmt} file. The only downloader.

    `url` may be any yt-dlp input, including a search like "ytsearch1:some query".
    Pass `title` to name the file yourself and skip the info round-trip - callers
    that already know the track name (e.g. Spotify) should.
    """
    logger.info("Starting download", extra={"url": url, "fmt": fmt, "quality": quality})
    base_dir = target_dir if target_dir else MEDIA_DIR
    os.makedirs(base_dir, exist_ok=True)

    if is_cancelled and is_cancelled():
        raise DownloadCancelled()
    opts = _base_opts(progress_callback, throttle, is_cancelled)
    if download_archive:
        opts["download_archive"] = download_archive
    try:
        if title is None:
            with yt_dlp.YoutubeDL({**opts, "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title", "downloaded_file")
            logger.info("Fetched info", extra={"title": title, "ext": info.get("ext")})

        if is_cancelled and is_cancelled():
            raise DownloadCancelled()
        if status_callback:
            status_callback("Downloading", title)
        if status_callback:
            opts["postprocessor_hooks"] = [_postprocessor_hook(
                lambda stage: status_callback(stage, title)
            )]

        # An all-non-ASCII title sanitizes to "", which would yield a bare ".mp3".
        safe_title = sanitize_filename(title) or "download"
        filename = f"{safe_title}.{fmt}"
        opts.update(_format_opts(fmt, quality, source_metadata))
        # Postprocessors decide the final extension; %(ext)s lets them.
        opts["outtmpl"] = os.path.join(base_dir, f"{safe_title}.%(ext)s")

        with yt_dlp.YoutubeDL(opts) as ydl:
            if fmt == "mp4" and crop != "Original":
                ydl.add_post_processor(CenterCropPostProcessor(ydl, crop))
            downloaded = ydl.extract_info(url, download=True)

        if downloaded is None:
            logger.info("Download skipped because it is already in the archive", extra={"url": url})
            return None
        logger.info("Conversion complete", extra={"path": os.path.join(base_dir, filename)})
        return filename
    except DownloadCancelled:
        raise
    except Exception as e:
        logger.error("Download/convert failed", extra={"url": url, "error": str(e)})
        raise


def download_selected(playlist_title, videos_dict, fmt, quality, target_dir=None,
                      progress_callback=None, status_callback=None, is_cancelled=None, crop="Original"):
    """Download the picked videos into a playlist subfolder and report prior downloads."""
    base_dir = target_dir if target_dir else MEDIA_DIR
    archive = playlist_archive_path(base_dir, playlist_title, fmt, quality)
    playlist_dir = archive.parent
    os.makedirs(playlist_dir, exist_ok=True)

    done, failed, skipped = [], [], []
    used_titles = {}
    items = list(videos_dict.items()) if isinstance(videos_dict, dict) else list(videos_dict)
    total = len(items)
    for idx, (title, url) in enumerate(items, start=1):
        if is_cancelled and is_cancelled():
            raise DownloadCancelled(done, failed + items[idx - 1:])
        title_key = (sanitize_filename(title) or "download").casefold()
        used_titles[title_key] = used_titles.get(title_key, 0) + 1
        output_title = _distinct_output_title(title, used_titles[title_key])
        if _archive_contains_url(archive, url):
            skipped.append(title)
        else:
            try:
                saved = download_and_convert(
                    url, fmt, quality, target_dir=playlist_dir, title=output_title, throttle=True,
                    progress_callback=progress_callback,
                    status_callback=(
                        lambda stage, name, item=idx: status_callback(stage, item, total, name)
                    ) if status_callback else None,
                    is_cancelled=is_cancelled,
                    download_archive=str(archive),
                    crop=crop,
                )
                if saved:
                    done.append(saved)
                else:
                    skipped.append(title)
            except DownloadCancelled:
                raise DownloadCancelled(done, failed + items[idx - 1:])
            except Exception as e:
                logger.error("Playlist item failed", extra={"title": title, "url": url, "error": str(e)})
                failed.append((title, url))
        if progress_callback:
            progress_callback(int(idx / total * 100) if total else 100)
    logger.info("Playlist complete", extra={"playlist": playlist_title,
                                            "downloaded": len(done), "skipped": len(skipped), "failed": len(failed)})
    return done, failed, skipped
