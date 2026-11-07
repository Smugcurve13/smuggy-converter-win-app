from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from audio_trim import default_trimmed_path
from core.audio_trim_worker import AudioTrimWorker


class AudioTrimDialog(QDialog):
    def __init__(self, folder: Path, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.source = None
        self.worker = None
        self.setWindowTitle("Trim Audio")
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        title = QLabel("Trim local audio")
        title.setObjectName("heading")
        layout.addWidget(title)
        subtitle = QLabel("Choose an audio file, set the start and end in seconds, then save a new MP3 copy. The original stays unchanged.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        source_row = QHBoxLayout()
        self.source_input = QLineEdit()
        self.source_input.setReadOnly(True)
        self.source_input.setMinimumHeight(38)
        browse = QPushButton("Choose Audio")
        browse.clicked.connect(self._choose_source)
        source_row.addWidget(self.source_input)
        source_row.addWidget(browse)
        layout.addLayout(source_row)

        times = QHBoxLayout()
        times.addWidget(QLabel("Start (seconds)"))
        self.start_input = QDoubleSpinBox()
        self.start_input.setRange(0, 86_400)
        self.start_input.setDecimals(3)
        self.start_input.setSingleStep(0.5)
        self.start_input.valueChanged.connect(self._update_state)
        times.addWidget(self.start_input)
        times.addWidget(QLabel("End (seconds)"))
        self.end_input = QDoubleSpinBox()
        self.end_input.setRange(0, 86_400)
        self.end_input.setDecimals(3)
        self.end_input.setSingleStep(0.5)
        self.end_input.valueChanged.connect(self._update_state)
        times.addWidget(self.end_input)
        layout.addLayout(times)

        layout.addWidget(QLabel("New file"))
        self.output_input = QLineEdit()
        self.output_input.setReadOnly(True)
        self.output_input.setMinimumHeight(38)
        layout.addWidget(self.output_input)

        actions = QHBoxLayout()
        actions.addStretch()
        self.trim_button = QPushButton("Trim Audio")
        self.trim_button.setObjectName("trim")
        self.trim_button.clicked.connect(self._start)
        actions.addWidget(self.trim_button)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        actions.addWidget(close)
        layout.addLayout(actions)
        self._update_state()
        self.setStyleSheet("""
            QDialog { background: #1b1b1f; }
            QLabel { color: #f2f3f7; }
            QLabel#heading { color: #f7f7fb; font-size: 28px; font-weight: 700; }
            QLabel#subtitle { color: #c2c7d1; font-size: 14px; }
            QLineEdit, QDoubleSpinBox { background: #0f0f13; color: #e9e9ef; border: 1px solid #2b2b31; border-radius: 7px; padding: 8px; }
            QPushButton { background: #2d2a2f; color: #f2f3f7; border: 1px solid #3a383f; border-radius: 7px; padding: 9px 14px; font-weight: 600; }
            QPushButton#trim { background: #e65050; border: none; color: white; font-size: 16px; }
            QPushButton:disabled { color: #777985; border-color: #2b2b31; }
        """)

    def _choose_source(self):
        selected, _ = QFileDialog.getOpenFileName(
            self, "Choose Audio", str(self.folder),
            "Audio Files (*.mp3 *.m4a *.wav *.flac *.aac *.ogg *.opus)",
        )
        if selected:
            self._set_source(Path(selected))

    def _set_source(self, source: Path):
        self.source = Path(source)
        self.source_input.setText(str(self.source))
        self.output_input.setText(str(default_trimmed_path(self.source)))
        self._update_state()

    def _update_state(self):
        ready = bool(self.source and self.end_input.value() > self.start_input.value())
        self.trim_button.setEnabled(ready)

    def _start(self):
        if not self.source:
            return
        destination = default_trimmed_path(self.source)
        self.output_input.setText(str(destination))
        self.trim_button.setText("Trimming audio…")
        self.trim_button.setEnabled(False)
        self.worker = AudioTrimWorker(
            self.source, self.start_input.value(), self.end_input.value(), destination, self,
        )
        self.worker.finished.connect(self._finished)
        self.worker.start()

    def _finished(self, success: bool, message: str):
        self.worker = None
        self.trim_button.setText("Trim Audio")
        self._update_state()
        if success:
            QMessageBox.information(self, "Audio Trimmed", f"Trimmed audio saved to:\n{message}")
        else:
            QMessageBox.warning(self, "Trim Failed", message)

    def reject(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Trim in progress", "Wait for the current trim to finish before closing this window.")
            return
        super().reject()
