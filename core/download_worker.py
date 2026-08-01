from pathlib import Path

from PySide6.QtCore import QThread, Signal

from playlist import extract_video_info_from_array
from downloader import download_and_convert, download_selected


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
            if "playlist" in self.mode:
                videos_dict = extract_video_info_from_array(self.selected_videos)
                download_selected(
                    self.playlist_title,
                    videos_dict,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                )
                self.finished.emit(True, f'{self.playlist_title} is saved', self.playlist_title)
            else:
                filename = download_and_convert(
                    self.url,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                )
                self.finished.emit(True, f'{filename} is saved', filename)
        except Exception as e:
            # downloader.py already logged this with full context; don't double-log.
            self.finished.emit(False, str(e), "")
