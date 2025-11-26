from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedLayout,
    QPushButton,
)

class CustomTabButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setStyleSheet(self.default_style())
        self.setAutoExclusive(False)

    def default_style(self):
        return """
            QPushButton {
                border: none;
                padding: 6px 12px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(100, 100, 100, 0.2);
            }
            QPushButton:checked {
                background-color: rgba(100, 100, 100, 0.4);
                font-weight: bold;
            }
        """

class CustomTabs(QWidget):
    def __init__(self, tabs=None, parent=None, preset="horizontal_dark", style_override=None):
        super().__init__(parent)

        # Set class variables
        self.tabs = tabs or []
        self.preset = preset
        self.style_override = style_override
        self.setObjectName("CustomTabs")
        self.orientation = (
            Qt.Horizontal if "horizontal" in preset else Qt.Vertical
        )

        # Tabs section
        self.tabs_widget = QWidget()
        self.tabs_widget.setObjectName("tabsWidget")
        self.tabs_layout = (
            QHBoxLayout() if self.orientation == Qt.Horizontal else QVBoxLayout()
        )
        self.tabs_widget.setLayout(self.tabs_layout)

        # Body section
        self.body_widget = QWidget()
        self.body_widget.setObjectName("tabBody")
        self.body_layout = QStackedLayout()
        self.body_widget.setLayout(self.body_layout)

        # Add tab and body contents
        self.buttons = []
        for index, (widget, title) in enumerate(self.tabs):
            button = CustomTabButton(title)
            button.setObjectName("tabButton")
            self.tabs_layout.addWidget(button)
            self.body_layout.addWidget(widget)
            button.clicked.connect(lambda checked, i=index: self.set_current_index(i))
            self.buttons.append(button)

        if self.buttons:
            self.set_current_index(0)

        if self.body_layout.count() > 0:
            self.body_layout.setCurrentIndex(0)
            self.tabs_layout.itemAt(0).widget().setChecked(True)

        # Build widget
        self.root_layout = (
            QVBoxLayout() if self.orientation == Qt.Horizontal else QHBoxLayout()
        )
        self.root_layout.addWidget(self.tabs_widget)
        self.root_layout.addWidget(self.body_widget)
        self.setLayout(self.root_layout)

    def set_current_index(self, index):
        self.body_layout.setCurrentIndex(index)
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)

    def set_stylesheet(self):
        preset_qss = self.PRESETS.get(self.preset, "")
        override_qss = self.style_override or ""
        self.setStyleSheet(preset_qss + override_qss)

    PRESETS = {
    "vertical_dark": """
        QWidget#CustomTabs {
            background: #222;
            border-radius: 8px;
        }
        QWidget#tabsWidget {
            background-color: #333;
            border-radius: 8px 8px 0 0;
        }
        QPushButton#tabButton {
            background-color: transparent;
            color: #ccc;
            padding: 6px 12px;
            border-radius: 6px;
        }
        QPushButton#tabButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        QPushButton#tabButton:checked {
            background-color: #555;
            font-weight: bold;
        }
        QWidget#tabBody {
            background-color: #111;
            border-radius: 8px;
            padding: 8px;
            border: 1px solid #888;
        }
    """,
    "horizontal_dark": """
        QWidget#CustomTabs {
            background: #222;
            border-radius: 8px;
        }
        QWidget#tabsWidget {
            background-color: #333;
            border-radius: 8px 8px 0 0;
        }
        QPushButton#tabButton {
            background-color: transparent;
            color: #ccc;
            padding: 6px 12px;
            border-radius: 6px;
        }
        QPushButton#tabButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        QPushButton#tabButton:checked {
            background-color: #555;
            font-weight: bold;
        }
        QWidget#tabBody {
            padding: 8px;
        }
    """,
}

