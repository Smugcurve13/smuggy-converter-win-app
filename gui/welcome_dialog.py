from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from release_notes import get_notes


class WelcomeDialog(QDialog):
    def __init__(self, version, onboarding, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to SmuggyConverter v{version}" if onboarding else "What's New")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)

        if onboarding:
            heading = QLabel(f"Welcome to SmuggyConverter v{version}")
            heading.setStyleSheet("font-size: 24px; font-weight: 700;")
            body.addWidget(heading)
            body.addWidget(QLabel(
                "<b>Getting Started</b><br>"
                "1. Choose YouTube Video, YouTube Playlist, Spotify, or Instagram.<br>"
                "2. Confirm the output folder, format, and quality.<br>"
                "3. Paste a URL or choose an Exportify CSV, then start.<br><br>"
                "Playlist runs can resume, your ordinary choices are remembered, and Spotify needs an Exportify CSV."
            ))

        body.addWidget(QLabel(f"<b>What's New in v{version}</b>"))
        for category in ("NEW", "CHANGED", "FIXED"):
            entries = get_notes(version).get(category, [])
            if entries:
                body.addWidget(QLabel(f"<b>{category.title()}</b><br>" + "<br>".join(f"• {entry}" for entry in entries)))
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.continue_button = QPushButton("Start Using SmuggyConverter" if onboarding else "Continue")
        self.continue_button.clicked.connect(self.accept)
        self.continue_button.setDefault(True)
        layout.addWidget(self.continue_button)
        self.setStyleSheet("QDialog { background: #1b1b1f; } QLabel { color: #f2f3f7; } QPushButton { background: #e65050; color: #fff; border: none; border-radius: 6px; padding: 10px; font-weight: 600; }")
