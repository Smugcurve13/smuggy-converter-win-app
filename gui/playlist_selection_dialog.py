from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
)


class PlaylistSelectionDialog(QDialog):
    """Dialog for selecting videos from a playlist."""
    
    def __init__(self, playlist_title: str, video_data: list, parent=None):
        super().__init__(parent)
        self.playlist_title = playlist_title
        self.video_data = video_data
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
        self.select_all_checkbox.setTristate(False)
        self.select_all_checkbox.setLayoutDirection(Qt.RightToLeft)
        self.select_all_checkbox.clicked.connect(self._toggle_select_all)
        select_all_layout.addWidget(self.select_all_checkbox)
        layout.addLayout(select_all_layout)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.itemChanged.connect(self._on_item_changed)
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
    
    def _on_item_changed(self, item):
        self._update_select_all_state()
    
    def _update_select_all_state(self):
        """Update Select All checkbox based on item states."""
        visible = 0
        checked = 0

        for i in range(self.video_list.count()):
            item = self.video_list.item(i)

            if item.isHidden():
                continue

            visible += 1

            if item.checkState() == Qt.Checked:
                checked += 1

        # Block signals to avoid triggering _toggle_select_all
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(visible > 0 and checked == visible)
        self.select_all_checkbox.blockSignals(False)
    
    def _toggle_select_all(self, checked):
        """Select or deselect all visible items."""
        visible_count = 0
        for i in range(self.video_list.count()):
            if not self.video_list.item(i).isHidden():
                visible_count += 1
        state_label = "checked" if checked else "unchecked"
        # logger.info("Select all toggled", extra={"state": state_label, "visible_count": visible_count})

        with QSignalBlocker(self.video_list):
            check_state = Qt.Checked if checked else Qt.Unchecked
            for i in range(self.video_list.count()):
                item = self.video_list.item(i)
                if not item.isHidden():
                    item.setCheckState(check_state)

        self._update_select_all_state()
    
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

