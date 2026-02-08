from pathlib import Path

from PySide6.QtCore import QThread, Signal

from playlist import extract_playlist_info, extract_video_info_from_array, selected_playlist_videos
from downloader import download_and_convert
from logs import logger

class DownloadWorker(QThread):
    """Worker thread for downloading and converting videos."""
    finished = Signal(bool, str, str)  # success, result_message, video_name
    progress = Signal(int)
    
    def __init__(self, mode: str, url: str, fmt: str, quality: int | None, output_dir: Path, selected_videos: list | None = None, playlist_title: str | None = None):
        super().__init__()
        self.mode = mode
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.output_dir = str(output_dir)
        self.selected_videos = selected_videos or []
        self.playlist_title = playlist_title or "playlist"
    
    def run(self):
        try:
            import os
            
            if "playlist" in self.mode:
                if self.selected_videos:
                    videos_dict = extract_video_info_from_array(self.selected_videos)

                    def progress_callback(percent):
                        self.progress.emit(percent)

                    selected_playlist_videos(self.playlist_title, videos_dict, self.fmt, self.quality, target_dir=self.output_dir, progress_callback=progress_callback)
                    self.finished.emit(True, f'{self.playlist_title} is saved', self.playlist_title)
                else:
                    # Download full playlist to a subfolder
                    name, results = extract_playlist_info(self.url)
                    # Extract playlist name - it's saved in a subdirectory
                    playlist_name = name
                    if results and len(results) > 0:
                        # Get the most recently created directory in output_dir
                        dirs = [d for d in os.listdir(self.output_dir) if os.path.isdir(os.path.join(self.output_dir, d))]
                        if dirs:
                            # Get the newest directory
                            newest_dir = max([os.path.join(self.output_dir, d) for d in dirs], key=os.path.getmtime)
                            playlist_name = os.path.basename(newest_dir)
                    self.finished.emit(True, f'{playlist_name} is saved', playlist_name)
            else:
                filename = download_and_convert(self.url, self.fmt, self.quality, target_dir=self.output_dir)
                self.finished.emit(True, f'{filename} is saved', filename)
        except Exception as e:
            logger.error("Download failed", extra={"error": str(e)})
            self.finished.emit(False, "Failure, please try again later", "")
