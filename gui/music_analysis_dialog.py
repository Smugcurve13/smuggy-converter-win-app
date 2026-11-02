from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.music_analysis_worker import MusicAnalysisWorker
from music_analysis import audio_files, export_csv


class MusicAnalysisDialog(QDialog):
    def __init__(self, folder: Path, parent=None):
        super().__init__(parent)
        self.folder = Path(folder)
        self.rows = []
        self.worker = None
        self.setWindowTitle("Analyze Music")
        self.resize(760, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel("Analyze local music")
        title.setObjectName("heading")
        layout.addWidget(title)
        subtitle = QLabel("Find BPM, musical key, and Camelot key. Files are not changed.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit(str(self.folder))
        self.folder_input.setReadOnly(True)
        self.folder_input.setMinimumHeight(38)
        browse = QPushButton("Choose Folder")
        browse.clicked.connect(self._choose_folder)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(browse)
        layout.addLayout(folder_row)

        self.file_count = QLabel()
        layout.addWidget(self.file_count)

        self.analyze_button = QPushButton("Analyze Music")
        self.analyze_button.setObjectName("analyze")
        self.analyze_button.clicked.connect(self._start)
        layout.addWidget(self.analyze_button)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.hide()
        layout.addWidget(self.progress)

        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(("File", "BPM", "Key", "Camelot"))
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.hide()
        layout.addWidget(self.results_table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        self.export_button = QPushButton("Export CSV")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        actions.addWidget(self.export_button)
        close = QPushButton("Close")
        close.clicked.connect(self.reject)
        actions.addWidget(close)
        layout.addLayout(actions)

        self._refresh_files()
        self.setStyleSheet("""
            QDialog { background: #1b1b1f; }
            QLabel { color: #f2f3f7; }
            QLabel#heading { color: #f7f7fb; font-size: 28px; font-weight: 700; }
            QLabel#subtitle { color: #c2c7d1; font-size: 14px; }
            QLineEdit, QTableWidget { background: #0f0f13; color: #e9e9ef; border: 1px solid #2b2b31; border-radius: 7px; padding: 8px; }
            QHeaderView::section { background: #232329; color: #e9e9ef; border: none; padding: 8px; font-weight: 600; }
            QPushButton { background: #2d2a2f; color: #f2f3f7; border: 1px solid #3a383f; border-radius: 7px; padding: 9px 14px; font-weight: 600; }
            QPushButton#analyze { background: #e65050; border: none; color: white; font-size: 16px; }
            QPushButton:disabled { color: #777985; border-color: #2b2b31; }
            QProgressBar { background: #0f0f13; color: #f2f3f7; border: 1px solid #2b2b31; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background: #e65050; border-radius: 5px; }
        """)

    def _refresh_files(self):
        self.paths = audio_files(self.folder) if self.folder.is_dir() else []
        self.file_count.setText(f"Found {len(self.paths)} supported audio file(s).")
        self.analyze_button.setEnabled(bool(self.paths))

    def _choose_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Choose Music Folder", str(self.folder))
        if selected:
            self.folder = Path(selected)
            self.folder_input.setText(str(self.folder))
            self.rows = []
            self.results_table.setRowCount(0)
            self.results_table.hide()
            self.export_button.setEnabled(False)
            self._refresh_files()

    def _start(self):
        if not self.paths:
            return
        self.analyze_button.setText("Cancel")
        self.analyze_button.clicked.disconnect()
        self.analyze_button.clicked.connect(self._cancel)
        self.progress.setValue(0)
        self.progress.show()
        self.worker = MusicAnalysisWorker(self.paths, self)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.progress.setFormat)
        self.worker.finished.connect(self._show_results)
        self.worker.start()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self._cancel()
            return
        super().reject()

    def _cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.analyze_button.setText("Cancelling…")
            self.analyze_button.setEnabled(False)

    def _show_results(self, rows, failures, cancelled):
        self.rows = rows
        self.progress.hide()
        self.analyze_button.setText("Analyze Music")
        self.analyze_button.setEnabled(bool(self.paths))
        self.analyze_button.clicked.disconnect()
        self.analyze_button.clicked.connect(self._start)
        self.results_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            values = (row["file"], f'{row["bpm"]:.1f}' if row["bpm"] else "", row["key"], row["camelot"])
            for column, value in enumerate(values):
                self.results_table.setItem(index, column, QTableWidgetItem(str(value)))
        self.results_table.setVisible(bool(rows))
        self.export_button.setEnabled(bool(rows))
        if failures or cancelled:
            parts = []
            if failures:
                parts.append(f"{len(failures)} file(s) could not be analyzed")
            if cancelled:
                parts.append("analysis was cancelled")
            self.file_count.setText(f"{len(rows)} result(s). " + "; ".join(parts) + ".")
        else:
            self.file_count.setText(f"Analyzed {len(rows)} file(s).")

    def _export(self):
        suggested = self.folder / "smuggyconverter-music-analysis.csv"
        destination, _ = QFileDialog.getSaveFileName(self, "Export Music Analysis", str(suggested), "CSV Files (*.csv)")
        if not destination:
            return
        try:
            export_csv(self.rows, Path(destination))
        except OSError as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not save the CSV:\n{exc}")
            return
        QMessageBox.information(self, "Export Complete", f"CSV saved to:\n{destination}")
