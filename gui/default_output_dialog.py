from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QDialog,
    QFileDialog
)

from logs import logger

class DefaultOutputDirDialog(QDialog):
    """Modal dialog for choosing the default output directory."""

    def __init__(self, start_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.selected_dir: Path | None = None
        self._start_dir = start_dir
        self.setWindowTitle("Set Default Output Folder")
        self.setModal(True)
        self.resize(560, 260)
        self._build_ui()
        self._apply_theme()

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #1b1b1f, stop:1 #0e0e11);
            }
            QLabel {
                color: #f2f3f7;
            }
            QLabel#titleLabel {
                color: #e65050;
                font-size: 20px;
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
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #c13232, stop:1 #c96851);
                border-radius: 8px;
                color: #fdfdff;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 18px;
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
            """
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Choose a default output folder")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        hint = QLabel("This location is used for all downloads unless you change it later.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText("Select a folder")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse)
        row.addWidget(self.path_input)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton("Use This Folder")
        self.ok_btn.setEnabled(False)
        self.ok_btn.clicked.connect(self._accept)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(self.ok_btn)
        layout.addLayout(button_row)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Output Folder", str(self._start_dir))
        if selected:
            self.selected_dir = Path(selected)
            self.path_input.setText(selected)
            self.ok_btn.setEnabled(True)

    def _accept(self) -> None:
        if self.selected_dir:
            self.accept()
