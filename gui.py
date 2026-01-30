"""
Static GUI prototype for SmuggyConverter.
Built with PySide6. No download/conversion functionality is wired yet.
"""
from pathlib import Path
import logging

from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QIcon
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
)

from downloader import download_and_convert, download_playlist
from config import ICON_PATH, ICO_ICON_PATH, OUTPUT_DIR_FILE


icon_path = Path(__file__).with_name(ICON_PATH)
ico_icon_path = Path(__file__).with_name(ICO_ICON_PATH)
output_dir_file = Path(__file__).with_name(OUTPUT_DIR_FILE)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

class ConverterWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SmuggyConverter")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1180, 760)
        self.setMinimumSize(960, 600)
        self.output_dir: Path | None = None
        self._load_output_dir()
        self._apply_theme()
        self._build_ui()
        QTimer.singleShot(0, self._post_init)
    
    def _post_init(self):
        if self.output_dir is None:
            self._prompt_initial_output_dir()
        else:
            self.output_path_edit.setText(str(self.output_dir))

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

    # def _badges(self) -> QHBoxLayout:
    #     layout = QHBoxLayout()
    #     layout.setSpacing(24)
    #     layout.addStretch()
    #     for text in ["Lightning Fast", "100% Safe", "No Registration"]:
    #         pill = self._badge(text)
    #         layout.addWidget(pill)
    #     layout.addStretch()
    #     return layout

    # def _badge(self, text: str) -> QWidget:
    #     pill = QWidget()
    #     pill.setObjectName("card")
    #     pill_layout = QHBoxLayout(pill)
    #     pill_layout.setContentsMargins(14, 8, 14, 8)
    #     icon = QLabel("*")  # Minimal ASCII marker; replace with icon later if desired.
    #     icon.setObjectName("pillText")
    #     label = QLabel(text)
    #     label.setObjectName("pillText")
    #     pill_layout.addWidget(icon)
    #     pill_layout.addSpacing(6)
    #     pill_layout.addWidget(label)
    #     return pill

    def _mode_switcher(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        label = QLabel("Choose Your Conversion Type")
        label.setAlignment(Qt.AlignCenter)
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
        self.convert_btn = QPushButton("Convert and Download")
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
        checked = self.mode_group.checkedButton()
        mode = checked.text().lower() if checked else "single"
        url = self.url_input.text().strip()
        fmt_text = self.format_combo.currentText().lower()
        fmt = "mp3" if "mp3" in fmt_text else "mp4"
        quality_text = self.quality_combo.currentText()
        digits = "".join(ch for ch in quality_text if ch.isdigit())
        quality = int(digits) if digits else None
        logger.info("Convert clicked", extra={"mode": mode, "url": url, "fmt": fmt, "quality": quality})
        if "playlist" in mode:
            return self._on_convert_playlist_clicked(url, fmt, quality)
        return self._on_convert_mp3_clicked(url, fmt, quality)
    
    def _on_convert_mp3_clicked(self, url: str, fmt: str, quality: int | None) -> None:
        logger.info("Single video conversion", extra={"url": url, "fmt": fmt, "quality": quality})
        return download_and_convert(url, fmt, quality)
    
    def _on_convert_playlist_clicked(self, url: str, fmt: str, quality: int | None) -> None:
        logger.info("Playlist conversion", extra={"url": url, "fmt": fmt, "quality": quality})
        return download_playlist(url, fmt, quality)


def main() -> None:
    app = QApplication([])
    window = ConverterWindow()
    window.showMaximized()
    tray_icon = QSystemTrayIcon(QIcon(str(icon_path)), parent=None)
    tray_icon.show()
    app.exec()


if __name__ == "__main__":
    main()
