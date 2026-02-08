from pathlib import Path
import subprocess
import platform
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
    QDialog,
    QMessageBox
)

from gui.default_output_dialog import DefaultOutputDirDialog
from gui.spinner_widget import SpinnerWidget
from gui.playlist_selection_dialog import PlaylistSelectionDialog
from core.download_worker import DownloadWorker

from playlist import extract_playlist_info
from config import icon_path, output_dir_file
from logs import logger


class ConverterWindow(QMainWindow):
    def _update_url_mode(self):
    # Safety check in case UI isn't built yet
        if not hasattr(self, "url_label") or not hasattr(self, "url_input"):
            return

        if self.mode_group.buttons()[1].isChecked():  # Playlist
            self.url_label.setText("YouTube Playlist URL:")
            self.url_input.setPlaceholderText("https://www.youtube.com/playlist?list=...")
        else:  # Single video
            self.url_label.setText("YouTube Video URL:")
            self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SmuggyConverter")
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
        QTimer.singleShot(0, self._post_init)
    
    def _post_init(self):
        if self.output_dir is None:
            self._prompt_initial_output_dir()
        else:
            self.output_path_edit.setText(str(self.output_dir))
    
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
            """
        )

    def _build_ui(self) -> None:
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

        self.setCentralWidget(central)

    def _hero(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        title_row = QHBoxLayout()
        title = QLabel("Convert YouTube Videos")
        title.setObjectName("headline")
        accent = QLabel("to MP3")
        accent.setObjectName("headlineAccent")
        title_row.addStretch()
        title_row.addWidget(title)
        title_row.addSpacing(10)
        title_row.addWidget(accent)
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
        
        for text in ["Single Video", "Playlist"]:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setObjectName("mode")
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
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._choose_output_dir)
        open_output_dir_btn = QPushButton("Open in Folder")
        open_output_dir_btn.clicked.connect(self._open_output_dir)
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(browse_btn)
        output_row.addWidget(open_output_dir_btn)

    # URL input
        self.url_label = QLabel("YouTube Video URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")

    # Format
        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP3 (Audio)"])

    # Quality
        quality_label = QLabel("Audio Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["320 kbps (Highest)", "256 kbps", "192 kbps"])

    # Build form layout
        form_grid.addWidget(output_label)
        form_grid.addLayout(output_row)
        form_grid.addWidget(self.url_label)
        form_grid.addWidget(self.url_input)
        form_grid.addWidget(format_label)
        form_grid.addWidget(self.format_combo)
        form_grid.addWidget(quality_label)
        form_grid.addWidget(self.quality_combo)

        card_layout.addLayout(form_grid)
    # Sync label with current mode (important)
        self._update_url_mode()
        return card

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
        
        checked = self.mode_group.checkedButton()
        mode = checked.text().lower() if checked else "single"
        url = self.url_input.text().strip()
        
        if not url:
            self._show_toast("Please enter a YouTube URL", False)
            return
        
        # Check if playlist URL is entered in single video mode
        if "playlist?list=" in url and "playlist" not in mode:
            self._show_toast("Playlist detected: switch modes", False)
            return
        
        fmt_text = self.format_combo.currentText().lower()
        fmt = "mp3" if "mp3" in fmt_text else "mp4"
        quality_text = self.quality_combo.currentText()
        digits = "".join(ch for ch in quality_text if ch.isdigit())
        quality = int(digits) if digits else None
        
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
            self._start_loading(show_progress=False)
            
            # Create and start worker thread
            self.worker = DownloadWorker(mode, url, fmt, quality, self.output_dir)
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
        else:
            logger.error("Download failed", extra={"error": message})

    def _on_download_progress(self, percent: int):
        self.progress_bar.setValue(percent)
    
    def _show_toast(self, message: str, is_success: bool):
        """Show a toast message to the user."""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Success" if is_success else "Error")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Information if is_success else QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # Apply custom styling
        msg_box.setStyleSheet("""
            QMessageBox {
                background: #1b1b1f;
            }
            QMessageBox QLabel {
                color: #f2f3f7;
                font-size: 14px;
            }
            QPushButton {
                background: #e65050;
                color: #fdfdff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #d33b3b;
            }
        """)
        
        msg_box.exec()