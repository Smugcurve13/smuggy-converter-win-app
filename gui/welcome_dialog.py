from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from release_notes import get_notes


class WelcomeDialog(QDialog):
    def __init__(self, version, onboarding, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to SmuggyConverter v{version}" if onboarding else f"What's New in v{version}")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)

        self.heading = QLabel(f"Welcome to SmuggyConverter v{version}" if onboarding else f"What's New in v{version}")
        self.heading.setObjectName("heading")
        self.heading.setWordWrap(True)
        body.addWidget(self.heading)

        if onboarding:
            getting_started = QLabel(
                "<b>Getting Started</b><br>"
                "1. Choose YouTube Video, YouTube Playlist, Spotify, or Instagram.<br>"
                "2. Confirm the output folder, format, and quality.<br>"
                "3. Paste a URL or choose an Exportify CSV, then start.<br><br>"
                "Your normal choices are remembered. Playlist downloads can resume, and Spotify uses an Exportify CSV."
            )
            getting_started.setObjectName("body")
            getting_started.setWordWrap(True)
            body.addWidget(getting_started)
        else:
            for category in ("NEW", "CHANGED", "FIXED"):
                entries = get_notes(version).get(category, [])
                if entries:
                    notes = QLabel(f"<b>{category.title()}</b><br>" + "<br>".join(f"• {entry}" for entry in entries))
                    notes.setObjectName("body")
                    notes.setWordWrap(True)
                    body.addWidget(notes)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.continue_button = QPushButton("Start Using SmuggyConverter" if onboarding else "Continue")
        self.continue_button.clicked.connect(self.accept)
        self.continue_button.setDefault(True)
        layout.addWidget(self.continue_button)
        self.setStyleSheet("QDialog { background: #1b1b1f; } QScrollArea, QScrollArea > QWidget > QWidget { background: #1b1b1f; border: none; } QLabel { color: #f2f3f7; font-size: 18px; } QLabel#heading { font-size: 30px; font-weight: 700; } QPushButton { background: #e65050; color: #fff; border: none; border-radius: 6px; padding: 12px; font-size: 16px; font-weight: 600; }")
