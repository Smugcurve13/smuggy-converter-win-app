from pathlib import Path

from PySide6.QtCore import QThread, Signal

from playlist import extract_video_info_from_array
from downloader import download_and_convert, download_selected
from spotify import download_spotify_csv
from instagram import download_instagram


class DownloadWorker(QThread):
    """Worker thread for downloading and converting videos."""
    finished = Signal(bool, str, str)  # success, result_message, video_name
    progress = Signal(int)

    def __init__(self, mode: str, url: str, fmt: str, quality: int | None, output_dir: Path, selected_videos: list | None = None, playlist_title: str | None = None, csv_path: str | None = None):
        super().__init__()
        self.mode = mode
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.output_dir = str(output_dir)
        self.selected_videos = selected_videos or []
        self.playlist_title = playlist_title or "playlist"
        self.csv_path = csv_path

    def run(self):
        try:
            if "spotify" in self.mode:
                done, failed = download_spotify_csv(
                    self.csv_path,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                )
                if not done:
                    raise Exception(f"No tracks could be downloaded ({len(failed)} failed)")
                msg = f"{len(done)} tracks saved"
                if failed:
                    msg += f", {len(failed)} failed: " + ", ".join(failed[:3])
                    if len(failed) > 3:
                        msg += f" and {len(failed) - 3} more"
                self.finished.emit(True, msg, "Spotify")
            elif "instagram" in self.mode:
                done, skipped = download_instagram(
                    self.url,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                )
                msg = done[0] + " is saved" if len(done) == 1 else f"{len(done)} files saved"
                if skipped:
                    msg += f", {len(skipped)} item(s) had no video"
                self.finished.emit(True, msg, done[0])
            elif "playlist" in self.mode:
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
