import json
import logging
import os
import re
from datetime import datetime, timezone

import ffmpeg
import yt_dlp
from ffmpeg import Error as FFmpegError
from file_utils import cleanup_file, generate_uuid_filename, get_media_path, MEDIA_DIR
# from .job_manager import update_job_progress

METADATA_EXT = ".metadata.json"

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Write metadata with timestamp
def write_metadata(file_id):
    metadata = {"timestamp": datetime.now(timezone.utc).isoformat()}
    meta_path = os.path.join(MEDIA_DIR, file_id + METADATA_EXT)
    with open(meta_path, "w") as f:
        json.dump(metadata, f)


def sanitize_filename(title):
    # Remove invalid filename characters and trim
    title = re.sub(r'[\\/:*?"<>|]', '', title)
    # Remove non-ASCII characters
    title = re.sub(r'[^\x00-\x7F]+', '', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Limit filename length (e.g., 100 chars)
    return title[:100]


def download_and_convert(url, fmt, quality):
    logger.info("Starting download", extra={"url": url, "fmt": fmt, "quality": quality})
    ext = fmt
    ydl_info_opts = {
        "quiet": True,
        "ignoreerrors": False,
        "noplaylist": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_info_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        logger.info("Fetched info", extra={"title": info.get('title'), "ext": info.get('ext')})
        title = info.get('title', 'downloaded_file')
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}.{ext}"
        target_path = get_media_path(filename)
        # Always download to a temp file to avoid in-place overwrite
        temp_filename = f"{safe_title}_temp.{info.get('ext', ext)}"
        temp_path = get_media_path(temp_filename)
        ydl_opts = {
            "outtmpl": temp_path,
            "format": "bestaudio/best" if fmt == "mp3" else "bestvideo+bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "ignoreerrors": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_path = ydl.prepare_filename(info)
            logger.info("Downloaded file", extra={"downloaded_path": downloaded_path})
            # If the downloaded file is already in the target format and name, just write metadata
            if os.path.abspath(downloaded_path) == os.path.abspath(target_path):
                write_metadata(filename)
                return filename
            # Conversion if needed
            if fmt == "mp3":
                try:
                    (
                        ffmpeg
                        .input(downloaded_path)
                        .output(target_path, audio_bitrate=f"{quality}k" if quality else "320k", format="mp3", acodec="libmp3lame")
                        .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                    )
                except FFmpegError as fe:
                    cleanup_file(downloaded_path)
                    err = fe.stderr.decode('utf-8', errors='ignore')
                    logger.error("FFmpeg mp3 error", extra={"error": err})
                    raise Exception(f"ffmpeg error: {err}")
                cleanup_file(downloaded_path)
                write_metadata(filename)
                print(f"Converted and saved: {filename}")
                logger.info("MP3 conversion complete", extra={"target_path": target_path})
                return filename
            elif fmt == "mp4":
                try:
                    (
                        ffmpeg
                        .input(downloaded_path)
                        .output(target_path, video_bitrate=f"{quality}k" if quality else None, format="mp4", vcodec="libx264", acodec="aac")
                        .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
                    )
                except FFmpegError as fe:
                    cleanup_file(downloaded_path)
                    err = fe.stderr.decode('utf-8', errors='ignore')
                    logger.error("FFmpeg mp4 error", extra={"error": err})
                    raise Exception(f"ffmpeg error: {err}")
                cleanup_file(downloaded_path)
                write_metadata(filename)
                logger.info("MP4 conversion complete", extra={"target_path": target_path})
                return filename
            else:
                raise ValueError("Invalid format")
    except Exception as e:
            logger.error("Download/convert failed", extra={"error": str(e)})
            raise Exception(f"Download/convert error: {e}")


def download_playlist(url, fmt, quality):
    logger.info("Starting playlist download", extra={"url": url, "fmt": fmt, "quality": quality})
    ydl_opts = {
        "extract_flat": True,
        "quiet": True,
        "ignoreerrors": True,
    }
    video_urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if "entries" in info:
                for entry in info["entries"]:
                    if entry and "id" in entry:
                        video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")
        logger.info("Playlist entries fetched", extra={"count": len(video_urls)})
    except Exception as e:
        # update_job_progress(job_id, 100, results=[{"error": f"Failed to extract playlist: {e}"}])
        print(f"Failed to extract playlist: {e}")
        logger.error("Failed to extract playlist", extra={"error": str(e)})
        return

    results = []
    total = len(video_urls)
    for idx, vurl in enumerate(video_urls):
        try:
            file_id = download_and_convert(vurl, fmt, quality)
            results.append({"url": vurl, "file_id": file_id, "status": "success"})
        except Exception as e:
            results.append({"url": vurl, "error": str(e), "status": "failed"})
            logger.error("Item failed", extra={"url": vurl, "error": str(e)})
        progress = int(((idx + 1) / total) * 100) if total else 100
        logger.info("Playlist progress", extra={"progress": progress, "completed": idx + 1, "total": total})
    return results
        # update_job_progress(job_id, progress, results=results)
    # update_job_progress(job_id, 100, results=results)


def download_batch(urls, fmt, quality, job_id):
    results = []
    total = len(urls)
    for idx, url in enumerate(urls):
        try:
            file_id = download_and_convert(url, fmt, quality)
            results.append({"url": url, "file_id": file_id, "status": "success"})
        except Exception as e:
            results.append({"url": url, "error": str(e), "status": "failed"})
        progress = int(((idx + 1) / total) * 100) if total else 100
        # update_job_progress(job_id, progress, results=results)
    # update_job_progress(job_id, 100, results=results)

if __name__ == "__main__":
    # Example usage
    test_url = "https://www.youtube.com/watch?v=DxsDekHDKXo"
    try:
        file_id = download_and_convert(test_url, "mp3", 320)
        print(f"Downloaded and converted file ID: {file_id}")
    except Exception as e:
        print(f"Error: {e}")