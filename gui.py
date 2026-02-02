"""
Static GUI prototype for SmuggyConverter.
Built with PySide6. No download/conversion functionality is wired yet.
"""
from pathlib import Path
import logging

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QRectF
from PySide6.QtGui import QIcon, QPainter, QPen, QColor, QConicalGradient
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSpacerItem,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
)

from downloader import download_and_convert, download_playlist
from extractor import extract_playlist_info
from config import ICON_PATH, ICO_ICON_PATH, OUTPUT_DIR_FILE

class SpinnerWidget(QWidget):
    """A custom spinning loader widget."""
    
    def __init__(self, parent=None, color=QColor(230, 80, 80), line_width=4):
        super().__init__(parent)
        self._angle = 0
        self._color = color
        self._line_width = line_width
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(40, 40)
        self.setAttribute(Qt.WA_TranslucentBackground)
    
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
    
    def start(self):
        self._timer.start(16)  # ~60 FPS
        self.show()
    
    def stop(self):
        self._timer.stop()
        self.hide()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate the drawing area
        side = min(self.width(), self.height())
        margin = self._line_width + 2
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)
        
        # Create gradient for the arc
        gradient = QConicalGradient(rect.center(), -self._angle)
        gradient.setColorAt(0, self._color)
        gradient.setColorAt(0.7, QColor(self._color.red(), self._color.green(), self._color.blue(), 50))
        gradient.setColorAt(1, QColor(self._color.red(), self._color.green(), self._color.blue(), 0))
        
        # Draw the spinning arc
        pen = QPen()
        pen.setBrush(gradient)
        pen.setWidth(self._line_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # Draw arc (270 degrees visible)
        start_angle = int(self._angle * 16)
        span_angle = 270 * 16
        painter.drawArc(rect, start_angle, span_angle)


icon_path = Path(__file__).with_name(ICON_PATH)
ico_icon_path = Path(__file__).with_name(ICO_ICON_PATH)
output_dir_file = Path(__file__).with_name(OUTPUT_DIR_FILE)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class PlaylistSelectionDialog(QDialog):
    """Dialog for selecting videos from a playlist."""
    
    def __init__(self, playlist_title: str, video_data: list, parent=None):
        super().__init__(parent)
        self.playlist_title = playlist_title
        self.video_data = video_data  # [[url, title, duration], ...]
        self.selected_videos = []
        self.setWindowTitle("Select Videos")
        self.setModal(True)
        self.resize(700, 600)
        self._build_ui()
        self._apply_theme()
    
    def _apply_theme(self):
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #1b1b1f, stop:1 #0e0e11);
            }
            QLabel {
                color: #f2f3f7;
            }
            QLabel#playlistTitle {
                color: #e65050;
                font-size: 24px;
                font-weight: 700;
            }
            QLineEdit {
                background: #0f0f13;
                color: #e9e9ef;
                border: 1px solid #2b2b31;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget {
                background: #0f0f13;
                color: #e9e9ef;
                border: 1px solid #2b2b31;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                padding-right: 30px;
            }
            QListWidget::item:hover {
                background: #2d2a2f;
            }
            QListWidget::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2b2b31;
                border-radius: 4px;
                background: #0f0f13;
                right: 8px;
            }
            QListWidget::indicator:checked {
                background: #e65050;
                border-color: #e65050;
            }
            QCheckBox {
                color: #f2f3f7;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2b2b31;
                border-radius: 4px;
                background: #0f0f13;
            }
            QCheckBox::indicator:checked {
                background: #e65050;
                border-color: #e65050;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #c13232, stop:1 #c96851);
                border-radius: 8px;
                color: #fdfdff;
                font-size: 16px;
                font-weight: 600;
                padding: 12px 24px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #d33b3b, stop:1 #d3745b);
            }
            QPushButton:pressed {
                background: #a92e2e;
            }
            QPushButton#cancelBtn {
                background: #2d2a2f;
            }
            QPushButton#cancelBtn:hover {
                background: #3d3a3f;
            }
        """)
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Playlist title
        title_label = QLabel(self.playlist_title)
        title_label.setObjectName("playlistTitle")
        layout.addWidget(title_label)
        
        # Search box
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search videos...")
        self.search_input.textChanged.connect(self._filter_list)
        layout.addWidget(search_label)
        layout.addWidget(self.search_input)
        
        # Select All checkbox (right-aligned)
        select_all_layout = QHBoxLayout()
        select_all_layout.addStretch()
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.setLayoutDirection(Qt.RightToLeft)
        self.select_all_checkbox.stateChanged.connect(self._toggle_select_all)
        select_all_layout.addWidget(self.select_all_checkbox)
        layout.addLayout(select_all_layout)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.itemClicked.connect(self._on_item_clicked)
        self._populate_list()
        layout.addWidget(self.video_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Convert Selected")
        ok_btn.clicked.connect(self._on_ok_clicked)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_list(self):
        """Populate the list with video data."""
        self.video_list.clear()
        for video in self.video_data:
            url, title, duration = video
            item_text = f"{title}  •  {duration}"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, video)  # Store full video data
            self.video_list.addItem(item)
    
    def _filter_list(self):
        """Filter the video list based on search text."""
        search_text = self.search_input.text().lower()
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            video_data = item.data(Qt.UserRole)
            _, title, _ = video_data
            item.setHidden(search_text not in title.lower())
        self._update_select_all_state()
    
    def _on_item_clicked(self, item):
        """Toggle checkbox when item is clicked."""
        current_state = item.checkState()
        new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
        item.setCheckState(new_state)
        self._update_select_all_state()
    
    def _update_select_all_state(self):
        """Update Select All checkbox based on item states."""
        visible_items = []
        checked_items = []
        
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if not item.isHidden():
                visible_items.append(item)
                if item.checkState() == Qt.Checked:
                    checked_items.append(item)
        
        # Block signals to avoid triggering _toggle_select_all
        self.select_all_checkbox.blockSignals(True)
        
        if len(visible_items) > 0 and len(checked_items) == len(visible_items):
            self.select_all_checkbox.setCheckState(Qt.Checked)
        elif len(checked_items) > 0:
            self.select_all_checkbox.setCheckState(Qt.PartiallyChecked)
        else:
            self.select_all_checkbox.setCheckState(Qt.Unchecked)
        
        self.select_all_checkbox.blockSignals(False)
    
    def _toggle_select_all(self, state):
        """Select or deselect all visible items."""
        check_state = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if not item.isHidden():
                item.setCheckState(check_state)
    
    def _on_ok_clicked(self):
        """Handle OK button click."""
        checked_items = []
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.checkState() == Qt.Checked:
                checked_items.append(item)
        
        if not checked_items:
            # Show warning if no videos selected
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Selection", "Please select at least one video.")
            return
        
        self.selected_videos = [item.data(Qt.UserRole) for item in checked_items]
        self.accept()


class DownloadWorker(QThread):
    """Worker thread for downloading and converting videos."""
    finished = Signal(bool, str, str)  # success, result_message, video_name
    
    def __init__(self, mode: str, url: str, fmt: str, quality: int | None, output_dir: Path):
        super().__init__()
        self.mode = mode
        self.url = url
        self.fmt = fmt
        self.quality = quality
        self.output_dir = str(output_dir)
    
    def run(self):
        try:
            import os
            
            if "playlist" in self.mode:
                # Download playlist to a subfolder
                # results = download_playlist(self.url, self.fmt, self.quality, target_dir=self.output_dir)
                name, results =  extract_playlist_info(self.url)
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


class ConverterWindow(QMainWindow):
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

        output_label = QLabel("Output Folder Path:")
        self.output_path_edit = QLineEdit(str(self.output_dir))
        self.output_path_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._choose_output_dir)
        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        output_row.addWidget(self.output_path_edit)
        output_row.addWidget(browse_btn)

        url_label = QLabel("YouTube Video URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")

        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        # format_combo.addItems(["MP3 (Audio)", "MP4 (Video)"])
        self.format_combo.addItems(["MP3 (Audio)"])

        quality_label = QLabel("Audio Quality:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["320 kbps (Highest)", "256 kbps", "192 kbps"])

        form_grid = QVBoxLayout()
        form_grid.setSpacing(10)
        form_grid.addWidget(output_label)
        form_grid.addLayout(output_row)
        form_grid.addWidget(url_label)
        form_grid.addWidget(self.url_input)
        form_grid.addWidget(format_label)
        form_grid.addWidget(self.format_combo)
        form_grid.addWidget(quality_label)
        form_grid.addWidget(self.quality_combo)

        card_layout.addLayout(form_grid)
        return card

    def _choose_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(self.output_dir))
        if selected:
            self.output_dir = Path(selected)
            self.output_path_edit.setText(str(self.output_dir))
            self._save_output_dir()

    def _prompt_initial_output_dir(self) -> None:
        start_dir = str(self.output_dir) if self.output_dir else str(Path.home())
        selected = QFileDialog.getExistingDirectory(
            self,
            "Please select a default output directory (this is a one time process)",
            start_dir,
        )
        if selected:
            self.output_dir = Path(selected)
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
                        # TODO: Process selected videos
                        self._show_toast(f"Selected {len(selected_videos)} videos. Download will start soon.", True)
                else:
                    logger.info("User cancelled playlist selection")
                    return
            except Exception as e:
                logger.error(f"Failed to extract playlist: {e}")
                self._show_toast(f"Failed to extract playlist: {str(e)}", False)
                return
        else:
            # Start spinner and disable button
            self._start_loading()
            
            # Create and start worker thread
            self.worker = DownloadWorker(mode, url, fmt, quality, self.output_dir)
            self.worker.finished.connect(self._on_download_finished)
            self.worker.start()
    
    def _start_loading(self):
        """Show spinner in button and disable it."""
        self.convert_btn.setText("")
        self.convert_btn.setEnabled(False)
        
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
        self.convert_btn.setText(self.original_button_text)
        self.convert_btn.setEnabled(True)
    
    def _on_download_finished(self, success: bool, message: str, video_name: str):
        """Handle download completion."""
        self._stop_loading()
        self._show_toast(message, success)
        
        if success:
            logger.info("Download completed successfully", extra={"video_name": video_name})
        else:
            logger.error("Download failed", extra={"message": message})
    
    def _show_toast(self, message: str, is_success: bool):
        """Show a toast message to the user."""
        from PySide6.QtWidgets import QMessageBox
        
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


def main() -> None:
    app = QApplication([])
    window = ConverterWindow()
    window.showMaximized()
    tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), parent=None)
    tray_icon.show()
    app.exec()


if __name__ == "__main__":
    main()
