from pathlib import Path
import subprocess
import platform
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QIcon, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QMessageBox,
    QProgressDialog
)

from gui.default_output_dialog import DefaultOutputDirDialog
from gui.spinner_widget import SpinnerWidget
from gui.playlist_selection_dialog import PlaylistSelectionDialog
from core.download_worker import DownloadWorker
from core.update_worker import UpdateCheckWorker, UpdateDownloadWorker

from playlist import extract_playlist_info
from config import icon_path, output_dir_file
from logs import logger, folder as logs_folder, create_logs_zip, default_zip_path
from version import __version__
import updater


class ConverterWindow(QMainWindow):
    def _current_mode(self) -> str:
        checked = self.mode_group.checkedButton()
        return checked.text().lower() if checked else "yt video"

    def _update_url_mode(self):
    # Safety check in case UI isn't built yet
        if not hasattr(self, "url_label") or not hasattr(self, "csv_row"):
            return

        mode = self._current_mode()
        spotify = "spotify" in mode

        # Spotify takes a CSV instead of a URL, and is always MP3.
        for w in (self.url_label, self.url_input, self.format_label, self.format_combo):
            w.setVisible(not spotify)
        for w in (self.csv_label, self.csv_row):
            w.setVisible(spotify)

        if spotify:
            self.accent.setText("from Spotify")
        elif "instagram" in mode:
            self.url_label.setText("Instagram Post or Reel URL:")
            self.url_input.setPlaceholderText("https://www.instagram.com/reel/...")
            self.accent.setText("from Instagram")
        elif "playlist" in mode:
            self.url_label.setText("YouTube Playlist URL:")
            self.url_input.setPlaceholderText("https://www.youtube.com/playlist?list=...")
            self.accent.setText(f"to {self._current_format().upper()}")
        else:
            self.url_label.setText("YouTube Video URL:")
            self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
            self.accent.setText(f"to {self._current_format().upper()}")

        # Unconditional: Spotify used to skip this, which left video resolutions
        # sitting under the "Audio Quality:" label.
        self._update_quality_options()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"SmuggyConverter v{__version__}")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1180, 760)
        self.original_button_text = "Convert and Download"
        self.setMinimumSize(960, 600)
        self.output_dir: Path | None = None
        self._load_output_dir()
        self._apply_theme()
        self._build_ui()
        self._init_spinner()
        self.worker = None
        # Separate slot from self.worker: the convert guard uses a single slot
        # and an update in flight would clobber a running conversion.
        self.update_worker = None
        QTimer.singleShot(0, self._post_init)

    def _post_init(self):
        if self.output_dir is None:
            self._prompt_initial_output_dir()
        else:
            self.output_path_edit.setText(str(self.output_dir))
        self._check_for_update()

    def _check_for_update(self) -> None:
        """Ask GitHub in the background. Stays silent unless there is an update."""
        self.update_worker = UpdateCheckWorker(self)
        self.update_worker.found.connect(self._on_update_available)
        self.update_worker.start()

    def _on_update_available(self, info: dict) -> None:
        size_mb = info.get("size", 0) / 1_000_000
        box = QMessageBox(self)
        box.setWindowTitle("Update Available")
        box.setText(f"SmuggyConverter {info['version']} is available.")
        box.setInformativeText(
            f"You are on v{__version__}. The download is about {size_mb:.0f} MB.\n"
            "SmuggyConverter will restart to finish installing."
        )
        box.setIcon(QMessageBox.Information)
        box.setStandardButtons(QMessageBox.NoButton)
        update_btn = box.addButton("Update Now", QMessageBox.AcceptRole)
        notes_btn = box.addButton("What's New", QMessageBox.ActionRole)
        box.addButton("Later", QMessageBox.RejectRole)
        box.setStyleSheet(self._toast_style())
        box.exec()

        clicked = box.clickedButton()
        if clicked is notes_btn:
            QDesktopServices.openUrl(QUrl(info["notes_url"]))
            return
        if clicked is not update_btn:
            logger.info("User deferred update", extra={"version": info["version"]})
            return

        # Fail here rather than after transferring 140 MB.
        reason = updater.blocked_reason(info.get("size", 0))
        if reason:
            logger.warning("Update not possible", extra={"reason": reason})
            self._show_update_error(f"{reason}\n\nYou can download it manually instead.",
                                    offer_page=True)
            return

        if self.worker and self.worker.isRunning():
            confirm = QMessageBox(self)
            confirm.setWindowTitle("Conversion in Progress")
            confirm.setText("Updating will stop the download that is running.")
            confirm.setIcon(QMessageBox.Warning)
            confirm.setStandardButtons(QMessageBox.Cancel)
            go_btn = confirm.addButton("Update Anyway", QMessageBox.AcceptRole)
            confirm.setStyleSheet(self._toast_style())
            confirm.exec()
            if confirm.clickedButton() is not go_btn:
                return

        self._start_update_download(info)

    def _start_update_download(self, info: dict) -> None:
        self.update_progress = QProgressDialog(
            f"Downloading SmuggyConverter {info['version']}...", "Cancel", 0, 100, self
        )
        self.update_progress.setWindowTitle("Updating")
        self.update_progress.setWindowModality(Qt.WindowModal)
        self.update_progress.setAutoClose(False)
        self.update_progress.setAutoReset(False)
        self.update_progress.setStyleSheet(self._toast_style())

        self.update_worker = UpdateDownloadWorker(info["url"], self)
        self.update_worker.progress.connect(self.update_progress.setValue)
        self.update_worker.finished.connect(self._on_update_downloaded)
        self.update_progress.canceled.connect(self.update_worker.cancel)
        self.update_worker.start()
        self.update_progress.show()

    def _on_update_downloaded(self, success: bool, result: str) -> None:
        self.update_progress.close()
        if not success:
            if result:  # empty means the user cancelled, which needs no dialog
                self._show_update_error(f"Could not download the update:\n{result}",
                                        offer_page=True)
            return

        self.update_progress.setLabelText("Installing...")
        try:
            updater.apply(Path(result))
        except Exception as exc:
            logger.error("Failed to stage update", extra={"error": str(exc)})
            self._show_update_error(f"Could not install the update:\n{exc}", offer_page=True)
            return

        logger.info("Update staged, quitting for swap")
        QApplication.quit()

    def _show_update_error(self, message: str, offer_page: bool = False) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Update Failed")
        box.setText(message)
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Ok)
        page_btn = box.addButton("Open Releases", QMessageBox.ActionRole) if offer_page else None
        box.setStyleSheet(self._toast_style())
        box.exec()
        if page_btn is not None and box.clickedButton() is page_btn:
            QDesktopServices.openUrl(QUrl(updater.RELEASES_URL))


    def _init_spinner(self):
        """Initialize the waiting spinner for the convert button."""
        self.spinner = SpinnerWidget(
            parent=self,
            color=QColor(255, 255, 255),  # White color for visibility on red button
            line_width=4
        )
        self.spinner.hide()

    def _apply_theme(self) -> None:
        # Global stylesheet keeps the dark, red-accented theme consistent.
        self.setStyleSheet(
            """
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                      stop:0 #1b1b1f, stop:1 #0e0e11); }
            QWidget#card { background: rgba(255, 255, 255, 0.02); border-radius: 14px; }
            QLabel#headline { color: #f7f7fb; font-size: 42px; font-weight: 800; }
            QLabel#headlineAccent { color: #e65050; font-size: 42px; font-weight: 800; }
            QLabel#subtitle { color: #c2c7d1; font-size: 16px; }
            QLabel#pillText { color: #c2c7d1; font-size: 13px; }
            QLabel { color: #f2f3f7; }
            QPushButton#mode { background: #17171b; color: #d9dbe2; border: 1px solid #2b2b31;
                               border-radius: 8px; padding: 10px 18px; font-weight: 600; }
            QPushButton#mode:checked { background: #2d2a2f; border-color: #e65050; color: #f5f5f7; }
            QPushButton#modeSpotify { background: #17171b; color: #d9dbe2; border: 1px solid #2b2b31;
                                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }
            QPushButton#modeSpotify:hover { background: #152112; border-color: #1db954; }
            QPushButton#modeSpotify:checked { background: #0d2b1a; border-color: #1ed760; color: #1ed760; }
            QPushButton#modeInstagram { background: #17171b; color: #d9dbe2; border: 1px solid #2b2b31;
                                        border-radius: 8px; padding: 10px 18px; font-weight: 600; }
            QPushButton#modeInstagram:hover { background: #24151f; border-color: #c13584; }
            QPushButton#modeInstagram:checked { background: #2b0d20; border-color: #e1306c; color: #e1306c; }
            QPushButton#convert { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                             stop:0 #c13232, stop:1 #c96851);
                                   border-radius: 10px; color: #fdfdff; font-size: 18px;
                                   font-weight: 700; padding: 16px; border: none; }
            QPushButton#convert:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                                    stop:0 #d33b3b, stop:1 #d3745b); }
            QPushButton#convert:pressed { background: #a92e2e; }
            QLineEdit, QComboBox { background: #0f0f13; color: #e9e9ef; border: 1px solid #2b2b31;
                                   border-radius: 8px; padding: 12px; font-size: 15px; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox QAbstractItemView { background: #0f0f13; selection-background-color: #2d2a2f;
                                          selection-color: #ffffff; }
            QFrame#line { background: #26262c; }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            """
        )

    def _build_ui(self) -> None:
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Create central widget for scrolling
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(36, 32, 36, 32)
        root.setSpacing(20)

        root.addItem(QSpacerItem(0, 12))
        root.addLayout(self._hero())
        # root.addItem(QSpacerItem(0, 12))
        # root.addLayout(self._badges())
        root.addItem(QSpacerItem(0, 12))
        root.addLayout(self._mode_switcher())
        root.addItem(QSpacerItem(0, 4))
        root.addWidget(self._form_card())
        root.addItem(QSpacerItem(0, 8))
        root.addLayout(self._footer())
        root.addStretch()  # Add stretch to push content to top

        scroll.setWidget(central)
        self.setCentralWidget(scroll)

    def _hero(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        title_row = QHBoxLayout()
        title = QLabel("Convert YouTube Videos")
        title.setObjectName("headline")
        self.accent = QLabel("to MP3")
        self.accent.setObjectName("headlineAccent")
        title_row.addStretch()
        title_row.addWidget(title)
        title_row.addSpacing(10)
        title_row.addWidget(self.accent)
        title_row.addStretch()
        layout.addLayout(title_row)
        
        subtitle = QLabel(
            "Download your favorite YouTube videos and playlists in high quality. Fast, free, and easy to use."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        return layout

    def _mode_switcher(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        label = QLabel("Choose Your Conversion Type")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold; color: #f2f3f7;")
        layout.addWidget(label)
        sub = QLabel("Paste any YouTube URL and select your preferred format and quality")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)
        modes = QHBoxLayout()
        modes.setSpacing(10)
        modes.addStretch()
        self.mode_group = QButtonGroup(self)
        self.mode_group.buttonClicked.connect(self._update_url_mode)
        
        for text in ["YT Video", "YT Playlist", "Spotify", "Instagram"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName({"Spotify": "modeSpotify", "Instagram": "modeInstagram"}.get(text, "mode"))
            self.mode_group.addButton(btn)
            modes.addWidget(btn)
        self.mode_group.buttons()[0].setChecked(True)
        modes.addStretch()
        layout.addLayout(modes)
        return layout

    def _form_card(self) -> QWidget:
        card = QWidget()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)
        form_grid = QVBoxLayout()
        form_grid.setSpacing(10)

    # Output folder row
        output_label = QLabel("Output Folder Path:")
        self.output_path_edit = QLineEdit(str(self.output_dir))
        self.output_path_edit.setReadOnly(True)
        self.output_path_edit.setMinimumHeight(42)
        browse_btn = QPushButton("Browse")
        browse_btn.setMinimumHeight(42)
        browse_btn.clicked.connect(self._choose_output_dir)
        open_output_dir_btn = QPushButton("Open in Folder")
        open_output_dir_btn.setMinimumHeight(42)
        open_output_dir_btn.clicked.connect(self._open_output_dir)
        open_logs_btn = QPushButton("Open Logs Folder")
        open_logs_btn.setMinimumHeight(42)
        open_logs_btn.clicked.connect(self._open_logs_folder)
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(browse_btn)
        output_row.addWidget(open_output_dir_btn)
        output_row.addWidget(open_logs_btn)

    # URL input
        self.url_label = QLabel("YouTube Video URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setMinimumHeight(42)

    # Exportify CSV (Spotify mode only)
        self.csv_label = QLabel("Exportify CSV File:")
        self.csv_input = QLineEdit()
        self.csv_input.setPlaceholderText("Export your playlist at exportify.net, then pick the CSV")
        self.csv_input.setReadOnly(True)
        self.csv_input.setMinimumHeight(42)
        csv_browse = QPushButton("Browse")
        csv_browse.setMinimumHeight(42)
        csv_browse.clicked.connect(self._choose_csv)
        csv_layout = QHBoxLayout()
        csv_layout.setSpacing(8)
        csv_layout.setContentsMargins(0, 0, 0, 0)
        csv_layout.addWidget(self.csv_input)
        csv_layout.addWidget(csv_browse)
        self.csv_row = QWidget()
        self.csv_row.setLayout(csv_layout)

    # Format
        self.format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3 (Audio)", "MP4 (Video)"])
        self.format_combo.setMinimumHeight(42)
        # _update_url_mode is the full refresh: labels, accent, visibility and
        # quality items. Format changes need all of it, not just the items.
        self.format_combo.currentTextChanged.connect(self._update_url_mode)

    # Quality
        self.quality_label = QLabel("Audio Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(42)

    # Build form layout
        form_grid.addWidget(output_label)
        form_grid.addLayout(output_row)
        form_grid.addWidget(self.url_label)
        form_grid.addWidget(self.url_input)
        form_grid.addWidget(self.csv_label)
        form_grid.addWidget(self.csv_row)
        form_grid.addWidget(self.format_label)
        form_grid.addWidget(self.format_combo)
        form_grid.addWidget(self.quality_label)
        form_grid.addWidget(self.quality_combo)

        card_layout.addLayout(form_grid)
    # Sync labels with current mode / format (important)
        self._update_quality_options()
        self._update_url_mode()
        return card

    def _choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Exportify CSV File", str(self.output_dir or Path.home()), "CSV Files (*.csv)"
        )
        if path:
            self.csv_input.setText(path)

    # (label, value). The value travels as Qt item data rather than being scraped
    # back out of the label, so labels may contain any number of digits.
    AUDIO_QUALITIES = [("320 kbps (Highest)", 320), ("256 kbps", 256), ("192 kbps", 192)]
    VIDEO_QUALITIES = [
        ("2160p (4K)", 2160),
        ("1440p (2K)", 1440),
        ("1080p", 1080),
        ("720p", 720),
        ("480p", 480),
    ]

    def _update_quality_options(self) -> None:
        """Owns the quality label and items. Mode decides first, format second.

        Spotify is always audio; it must never inherit the format combo's state,
        which is how video resolutions ended up under "Audio Quality:".
        """
        if "spotify" in self._current_mode() or self._current_format() == "mp3":
            self.quality_label.setText("Audio Quality:")
            entries = self.AUDIO_QUALITIES
        else:
            self.quality_label.setText("Video Quality:")
            entries = self.VIDEO_QUALITIES

        previous = self.quality_combo.currentData()
        self.quality_combo.clear()
        for label, value in entries:
            self.quality_combo.addItem(label, value)
        # Keep the user's pick when switching modes, if it still exists.
        keep = self.quality_combo.findData(previous)
        if keep != -1:
            self.quality_combo.setCurrentIndex(keep)

    def _current_format(self) -> str:
        return "mp3" if "mp3" in self.format_combo.currentText().lower() else "mp4"

    def _choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(self.output_dir))
        if selected:
            self.output_dir = Path(selected)
            self.output_path_edit.setText(str(self.output_dir))
            self._save_output_dir()
    
    def _open_output_dir(self) -> None:
        if self.output_dir and self.output_dir.exists():

            path = str(self.output_dir)
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", path])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", path])

    def _open_logs_folder(self) -> None:
        path = str(logs_folder)
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _prompt_initial_output_dir(self) -> None:
        start_dir = self.output_dir if self.output_dir else Path.home()
        dialog = DefaultOutputDirDialog(start_dir, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_dir:
            self.output_dir = dialog.selected_dir
            self.output_path_edit.setText(str(self.output_dir))
            self._save_output_dir()

    def _load_output_dir(self) -> None:
        if output_dir_file.exists():
            try:
                stored = output_dir_file.read_text(encoding="utf-8").strip()
                if stored:
                    candidate = Path(stored)
                    if candidate.exists() and candidate.is_dir():
                        self.output_dir = candidate
                        logger.info("Loaded stored output directory", extra={"output_dir": stored})
            except OSError:
                pass

    def _save_output_dir(self) -> None:
        if self.output_dir:
            try:
                output_dir_file.write_text(str(self.output_dir), encoding="utf-8")
                logger.info("Saved output directory", extra={"output_dir": str(self.output_dir)})
            except OSError as exc:
                logger.error("Failed to save output directory", extra={"error": str(exc)})

    def _footer(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        self.convert_btn = QPushButton(self.original_button_text)
        self.convert_btn.setObjectName("convert")
        self.convert_btn.setMinimumHeight(50)
        self.convert_btn.clicked.connect(self._on_convert_clicked)
        layout.addSpacing(4)
        layout.addWidget(self.convert_btn)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        layout.addSpacing(8)

        note = QLabel("Keep SmuggyConverter open during download to avoid interruptions")
        note.setAlignment(Qt.AlignCenter)
        note.setObjectName("subtitle")
        layout.addWidget(note)
        return layout

    def _on_convert_clicked(self) -> None:
        if self.worker and self.worker.isRunning():
            return  # Prevent multiple simultaneous downloads
        
        mode = self._current_mode()
        quality = self.quality_combo.currentData()

        if "spotify" in mode:
            csv_path = self.csv_input.text().strip()
            if not csv_path:
                self._show_toast("Please select an Exportify CSV file", False)
                return
            if not os.path.exists(csv_path):
                self._show_toast("The selected CSV file no longer exists", False)
                return
            logger.info("Convert clicked", extra={"mode": mode, "csv": csv_path, "quality": quality})
            self._start_loading(show_progress=True)
            self.worker = DownloadWorker(mode, "", "mp3", quality, self.output_dir, csv_path=csv_path)
            self.worker.progress.connect(self._on_download_progress)
            self.worker.finished.connect(self._on_download_finished)
            self.worker.start()
            return

        url = self.url_input.text().strip()
        instagram = "instagram" in mode

        if not url:
            self._show_toast(
                "Please enter an Instagram URL" if instagram else "Please enter a YouTube URL",
                False,
            )
            return

        fmt = self._current_format()

        if instagram:
            if "instagram.com" not in url:
                self._show_toast("That doesn't look like an Instagram URL", False)
                return
            logger.info("Convert clicked", extra={"mode": mode, "url": url, "fmt": fmt, "quality": quality})
            self._start_loading(show_progress=True)
            self.worker = DownloadWorker(mode, url, fmt, quality, self.output_dir)
            self.worker.progress.connect(self._on_download_progress)
            self.worker.finished.connect(self._on_download_finished)
            self.worker.start()
            return

        # Check if playlist URL is entered in single video mode
        if "playlist?list=" in url and "playlist" not in mode:
            self._show_toast("Playlist detected: switch modes", False)
            return

        logger.info("Convert clicked", extra={"mode": mode, "url": url, "fmt": fmt, "quality": quality})

        # If playlist mode, show selection dialog first
        if "playlist" in mode:
            try:
                # Extract playlist info
                playlist_title, video_data = extract_playlist_info(url)
                
                if not video_data:
                    self._show_toast("Failed to extract playlist information", False)
                    return
                
                # Show selection dialog
                dialog = PlaylistSelectionDialog(playlist_title, video_data, self)
                if dialog.exec() == QDialog.Accepted:
                    selected_videos = dialog.selected_videos
                    if selected_videos:
                        logger.info(f"User selected {len(selected_videos)} videos from playlist")
                        self._start_loading(show_progress=True)
                        self.worker = DownloadWorker(mode, url, fmt, quality, self.output_dir, selected_videos=selected_videos, playlist_title=playlist_title)
                        self.worker.progress.connect(self._on_download_progress)
                        self.worker.finished.connect(self._on_download_finished)
                        self.worker.start()
                else:
                    logger.info("User cancelled playlist selection")
                    return
            except Exception as e:
                logger.error(f"Failed to extract playlist: {str(e)}")
                self._show_toast(f"Failed to extract playlist: {str(e)}", False)
                return
        else:
            # Start spinner and disable button
            self._start_loading(show_progress=True)

            # Create and start worker thread
            self.worker = DownloadWorker(mode, url, fmt, quality, self.output_dir)
            self.worker.progress.connect(self._on_download_progress)
            self.worker.finished.connect(self._on_download_finished)
            self.worker.start()
    
    def _start_loading(self, show_progress: bool = False):
        """Show spinner in button and disable it."""
        self.convert_btn.setText("")
        self.convert_btn.setEnabled(False)
        if show_progress:
            self.progress_bar.setValue(0)
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
        
        # Position spinner in the center of the button
        self.spinner.setParent(self.convert_btn)
        button_rect = self.convert_btn.rect()
        spinner_x = (button_rect.width() - self.spinner.width()) // 2
        spinner_y = (button_rect.height() - self.spinner.height()) // 2
        self.spinner.move(spinner_x, spinner_y)
        self.spinner.start()
    
    def _stop_loading(self):
        """Stop spinner and restore button."""
        self.spinner.stop()
        self.spinner.setParent(self)
        self.spinner.hide()
        self.progress_bar.hide()
        self.progress_bar.setValue(0)
        self.convert_btn.setText(self.original_button_text)
        self.convert_btn.setEnabled(True)
    
    def _on_download_finished(self, success: bool, message: str, video_name: str):
        """Handle download completion."""
        self._stop_loading()
        self._show_toast(message, success)
        
        if success:
            logger.info("Download completed successfully", extra={"video_name": video_name})
        # Failures are already logged with full context in downloader.py.

    def _on_download_progress(self, percent: int):
        self.progress_bar.setValue(percent)
    
    def _show_toast(self, message: str, is_success: bool):
        """Show a toast message to the user."""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Success" if is_success else "Error")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information if is_success else QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        if not is_success:
            export_btn = msg_box.addButton("Export Logs", QMessageBox.ActionRole)
        else:
            export_btn = None
        
        msg_box.setStyleSheet(self._toast_style())
        
        msg_box.exec()

        if export_btn is not None and msg_box.clickedButton() is export_btn:
            self._export_logs_dialog()

    def _export_logs_dialog(self) -> None:
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Save Logs Zip",
            default_zip_path(),
            "Zip Files (*.zip)",
        )
        if not dest:
            return
        try:
            zip_path = create_logs_zip(dest)
            logger.info("Logs exported to %s", zip_path)
            ok = QMessageBox(self)
            ok.setWindowTitle("Export Successful")
            ok.setText(f"Logs saved to:\n{zip_path}")
            ok.setIcon(QMessageBox.Information)
            ok.setStandardButtons(QMessageBox.Ok)
            ok.setStyleSheet(self._toast_style())
            ok.exec()
        except Exception as exc:
            logger.error("Failed to export logs: %s", exc)
            err = QMessageBox(self)
            err.setWindowTitle("Export Failed")
            err.setText(f"Could not export logs:\n{exc}")
            err.setIcon(QMessageBox.Warning)
            err.setStandardButtons(QMessageBox.Ok)
            err.setStyleSheet(self._toast_style())
            err.exec()

    def _toast_style(self) -> str:
        return """
            QMessageBox { background: #1b1b1f; }
            QMessageBox QLabel { color: #f2f3f7; font-size: 14px; }
            QPushButton { background: #e65050; color: #fdfdff; border: none;
                          border-radius: 6px; padding: 8px 16px; font-weight: 600; }
            QPushButton:hover { background: #d33b3b; }
        """