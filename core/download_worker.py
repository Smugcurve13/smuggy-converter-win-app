from pathlib import Path

from PySide6.QtCore import QThread, Signal

from playlist import extract_video_info_from_array
from downloader import DownloadCancelled, DownloadFailed, download_and_convert, download_selected
from spotify import _track_name, download_spotify_csv, read_exportify_csv
from instagram import download_instagram


class DownloadWorker(QThread):
    """Worker thread for downloading and converting videos."""
    finished = Signal(bool, str, str)  # success, result_message, video_name
    progress = Signal(int)
    status = Signal(str)

    def __init__(self, mode: str, url: str, fmt: str, quality: int | None, output_dir: Path, selected_videos: list | None = None, playlist_title: str | None = None, csv_path: str | None = None, retry_items: list | None = None):
        super().__init__()
        self.mode = mode
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.output_dir = str(output_dir)
        self.selected_videos = selected_videos or []
        self.playlist_title = playlist_title or "playlist"
        self.csv_path = csv_path
        self.retry_items = retry_items or []
        self.result = {}
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    def is_cancelled(self):
        return self._cancel_requested

    def _status(self, stage, position, total, name):
        self.status.emit(f"{stage} {position} of {total} — {name}")

    def _finish(self, state, message, label, saved, failed=(), retry_items=()):
        self.result = {
            "state": state,
            "saved": list(saved),
            "failed": list(failed),
            "retry_items": list(retry_items),
            "output_dir": self.output_dir,
        }
        self.finished.emit(state == "Completed", message, label)

    def run(self):
        try:
            if "spotify" in self.mode:
                tracks = self.retry_items or read_exportify_csv(self.csv_path)
                done, failed = download_spotify_csv(
                    self.csv_path,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                    status_callback=self._status,
                    is_cancelled=self.is_cancelled,
                    tracks=tracks,
                )
                if self.is_cancelled():
                    raise DownloadCancelled(done)
                retry_items = failed
                failed = [_track_name(track) for track in failed]
                if not done:
                    self._finish("Failed", f"No tracks could be downloaded ({len(failed)} failed)", "Spotify", [], failed, retry_items)
                    return
                msg = f"{len(done)} tracks saved"
                if failed:
                    msg += f", {len(failed)} failed: " + ", ".join(failed[:3])
                    if len(failed) > 3:
                        msg += f" and {len(failed) - 3} more"
                state = "Completed with issues" if failed else "Completed"
                self._finish(state, msg, "Spotify", done, failed, retry_items)
            elif "instagram" in self.mode:
                done, skipped = download_instagram(
                    self.url,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                    status_callback=self._status,
                    is_cancelled=self.is_cancelled,
                    retry_items=self.retry_items,
                )
                if self.is_cancelled():
                    raise DownloadCancelled(done)
                msg = done[0] + " is saved" if len(done) == 1 else f"{len(done)} files saved"
                if skipped:
                    msg += f", {len(skipped)} item(s) had no video"
                state = "Completed with issues" if skipped else "Completed"
                self._finish(state, msg, done[0], done, skipped, skipped)
            elif "playlist" in self.mode:
                videos_dict = extract_video_info_from_array(self.selected_videos)
                done, failed = download_selected(
                    self.playlist_title,
                    videos_dict,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                    status_callback=self._status,
                    is_cancelled=self.is_cancelled,
                )
                if self.is_cancelled():
                    raise DownloadCancelled(done)
                failed_items = [video for video in self.selected_videos if video[0] in {url for _, url in failed}]
                failed = [title for title, _ in failed]
                retry_items = failed_items
                if not done:
                    self._finish("Failed", f"No tracks could be downloaded ({len(failed)} failed)", "", [], failed, retry_items)
                    return
                msg = f"{len(done)} tracks saved"
                if failed:
                    msg += f", {len(failed)} failed: " + ", ".join(failed[:3])
                    if len(failed) > 3:
                        msg += f" and {len(failed) - 3} more"
                state = "Completed with issues" if failed else "Completed"
                self._finish(state, msg, self.playlist_title, done, failed, retry_items)
            else:
                filename = download_and_convert(
                    self.url,
                    self.fmt,
                    self.quality,
                    target_dir=self.output_dir,
                    progress_callback=self.progress.emit,
                    status_callback=lambda stage, name: self._status(stage, 1, 1, name),
                    is_cancelled=self.is_cancelled,
                )
                if self.is_cancelled():
                    raise DownloadCancelled([filename])
                self._finish("Completed", f'{filename} is saved', filename, [filename])
        except DownloadCancelled as cancelled:
            label = self.playlist_title if "playlist" in self.mode else ("Spotify" if "spotify" in self.mode else "")
            self._finish(
                "Cancelled", f"Cancelled — {len(cancelled.saved)} saved", label,
                cancelled.saved, retry_items=cancelled.retry_items,
            )
        except DownloadFailed as failed:
            self._finish("Failed", str(failed), "", [], failed.failed, failed.retry_items)
        except Exception as e:
            # downloader.py already logged this with full context; don't double-log.
            retry_items = [self.url] if "instagram" in self.mode else []
            self._finish("Failed", str(e), "", [], retry_items=retry_items)
