import os
import yt_dlp
import datetime
import logging
import ffmpeg
from ffmpeg import Error as FFmpegError

from file_utils import MEDIA_DIR, sanitize_filename, cleanup_file

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def extract_playlist_info(url):
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "ignoreerrors": True,
    }
    final_array = []
    playlist_title = "playlist"
    ydl = yt_dlp.YoutubeDL(ydl_opts)
    try:
        info = ydl.extract_info(url, download=False)
        # print(type(info))
        # with open("test/debug_info.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(info, indent=4))
        playlist_title = info.get("title", playlist_title)
        if "entries" in info:
            for entry in info["entries"]:
                if entry and "id" in entry:
                    beech_ka_array = []
                    beech_ka_array.append(f"https://www.youtube.com/watch?v={entry['id']}")
                    beech_ka_array.append(entry.get("title", "Unknown"))
                    time = str(datetime.timedelta(seconds=entry.get("duration", 0)))
                    beech_ka_array.append(time)
                    final_array.append(beech_ka_array)
        #     print(final_array)
        
        # with open("test/playlist_info.json", "w", encoding="utf-8") as f:
        #     f.write(json.dumps(final_array, indent=4))
        return playlist_title, final_array
    except Exception as e:
        logger.error(f"Failed to extract playlist: {e}")
        return {
            "error": str(e)
        }
    
def extract_video_info_from_array(final_array):
    videos_dict = {}
    for array in final_array:
        # for item in array:
        key = array[1]
        value = array[0]
        videos_dict[key] = value
    return videos_dict

# def yt_downloader(videos_dict, fmt, target_dir=None):
#     for key,value in videos_dict.items():
#         logger.info(f"Downloading: {key}")
#         base_dir = target_dir if target_dir else MEDIA_DIR
#         logger.info(f"Target Directory: {base_dir}")
#         if not os.path.exists(base_dir):
#             os.makedirs(base_dir, exist_ok=True)
#         ext = fmt
#         title = sanitize_filename(key)
#         filepath = os.path.join(base_dir, f"{title}.{ext}") 
#         ydl_opts = {
#             "outtmpl": filepath,
#             "format": "bestaudio/best",
#             "noplaylist": True,
#             "quiet": True,
#             "ignoreerrors": True,
#         }
#         ydl = yt_dlp.YoutubeDL(ydl_opts)
#         try:
#             ydl.download([value])
#             logger.info(f"Downloaded: {filepath}")
#         except Exception as e:
#             logger.error(f"Failed to download {value}: {e}")

def selected_playlist_videos(playlist_title, videos_dict, fmt, quality, target_dir=None, progress_callback=None):
    base_dir = target_dir if target_dir else MEDIA_DIR
    playlist_title_safe = sanitize_filename(playlist_title)
    playlist_dir = os.path.join(base_dir, playlist_title_safe)
    if not os.path.exists(playlist_dir):
        os.makedirs(playlist_dir, exist_ok=True)
    ext = fmt
    results = []
    total = len(videos_dict)
    try:
        for idx, (key, value) in enumerate(videos_dict.items()):
            title = key
            safe_title = sanitize_filename(title)
            filename = f"{safe_title}.{ext}"
            target_path = os.path.join(playlist_dir, filename)
            # Always download to a temp file to avoid in-place overwrite
            temp_filename = f"{safe_title}_temp.{ext}"
            temp_path = os.path.join(playlist_dir, temp_filename)
            ydl_opts = {
                "outtmpl": temp_path,
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "ignoreerrors": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(value, download=True)
                downloaded_path = ydl.prepare_filename(info)
                logger.info("Downloaded file", extra={"downloaded_path": downloaded_path})
                # If the downloaded file is already in the target format and name, just write metadata
                if os.path.abspath(downloaded_path) == os.path.abspath(target_path):
                    # write_metadata(filename, playlist_dir)
                    results.append(filename)
                    if progress_callback:
                        progress = int(((idx + 1) / total) * 100) if total else 100
                        progress_callback(progress)
                    continue
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
                    # write_metadata(filename, playlist_dir)
                    print(f"Converted and saved: {filename}")
                    logger.info("MP3 conversion complete", extra={"target_path": target_path})
                    results.append(filename)
                    if progress_callback:
                        progress = int(((idx + 1) / total) * 100) if total else 100
                        progress_callback(progress)
                        
                else:
                    raise ValueError("Invalid format")
        return results
    except Exception as e:
        logger.error("Download/convert failed", extra={"error": str(e)})
        raise Exception(f"Download/convert error: {e}")

def single_url_downloader(videos_dict, fmt, quality, target_dir=None):
#     base_dir = target_dir if target_dir else MEDIA_DIR
#     if not os.path.exists(base_dir):
#         os.makedirs(base_dir, exist_ok=True)
#     ext = fmt
#     results = []
#     try:
#         for key, value in videos_dict.items():
#             title = key
#             safe_title = sanitize_filename(title)
#             filename = f"{safe_title}.{ext}"
#             target_path = os.path.join(base_dir, filename)
#             # Always download to a temp file to avoid in-place overwrite
#             temp_filename = f"{safe_title}_temp.{ext}"
#             temp_path = os.path.join(base_dir, temp_filename)
#             ydl_opts = {
#                 "outtmpl": temp_path,
#                 "format": "bestaudio/best",
#                 "noplaylist": True,
#                 "quiet": True,
#                 "ignoreerrors": False,
#             }
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 info = ydl.extract_info(value, download=True)
#                 downloaded_path = ydl.prepare_filename(info)
#                 logger.info("Downloaded file", extra={"downloaded_path": downloaded_path})
#                 # If the downloaded file is already in the target format and name, just write metadata
#                 if os.path.abspath(downloaded_path) == os.path.abspath(target_path):
#                     # write_metadata(filename, base_dir)
#                     results.append(filename)
#                     continue
#                 # Conversion if needed
#                 if fmt == "mp3":
#                     try:
#                         (
#                             ffmpeg
#                             .input(downloaded_path)
#                             .output(target_path, audio_bitrate=f"{quality}k" if quality else "320k", format="mp3", acodec="libmp3lame")
#                             .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
#                         )
#                     except FFmpegError as fe:
#                         cleanup_file(downloaded_path)
#                         err = fe.stderr.decode('utf-8', errors='ignore')
#                         logger.error("FFmpeg mp3 error", extra={"error": err})
#                         raise Exception(f"ffmpeg error: {err}")
#                     cleanup_file(downloaded_path)
#                     # write_metadata(filename, base_dir)
#                     print(f"Converted and saved: {filename}")
#                     logger.info("MP3 conversion complete", extra={"target_path": target_path})
#                     results.append(filename)
    # elif fmt == "mp4":
    #     try:
    #         (
    #             ffmpeg
    #             .input(downloaded_path)
    #             .output(target_path, video_bitrate=f"{quality}k" if quality else None, format="mp4", vcodec="libx264", acodec="aac")
    #             .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
    #         )
    #     except FFmpegError as fe:
    #         cleanup_file(downloaded_path)
    #         err = fe.stderr.decode('utf-8', errors='ignore')
    #         logger.error("FFmpeg mp4 error", extra={"error": err})
    #         raise Exception(f"ffmpeg error: {err}")
    #     cleanup_file(downloaded_path)
    #     # write_metadata(filename, base_dir)
    #     logger.info("MP4 conversion complete", extra={"target_path": target_path})
    #     return filename
#                 else:
#                     raise ValueError("Invalid format")
#         return results
#     except Exception as e:
#         logger.error("Download/convert failed", extra={"error": str(e)})
#         raise Exception(f"Download/convert error: {e}")
    pass


def selected_download_playlist_videos(url):
    pass

        

if __name__ == "__main__":
    # test_url = "https://youtube.com/playlist?list=PLVbLhzs-GWDkgYKkvn0g96K5HuccMd7yH&si=1_n89kCKwVBMD0bQ"
    test_url = "https://youtube.com/playlist?list=PLVbLhzs-GWDlLzYxbIDbyhDVrHgnLjCAP&si=ckeVOUOwkeXjRikM"
    name, final_array = extract_playlist_info(test_url)
    print(f"Playlist Title: {name}")
    videos_dict = extract_video_info_from_array(final_array)
    # print(f"URL: {url}, Title: {title}")
    print(f"Videos Dict: {videos_dict}")
    selected_playlist_videos(name, videos_dict, "mp3", "192")