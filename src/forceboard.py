from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QLabel, QMainWindow,
    QWidget, QTabWidget, QSpacerItem, QSizePolicy, QPushButton,
)
from board_status import BoardStatus
from widgets.custom_tabs import CustomTabs
from boards.wii_board import WiiBalanceBoard
from boards.balance_board_reader import BalanceBoardReader
from dashboard import Dashboard

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ForceBoard")
        self.resize(1000, 600)

        # Title Widget
        self.title_widget = QWidget()
        self.title_widget.setObjectName("titleWidget")
        self.title_layout = QHBoxLayout()

        self.logo = QLabel()
        self.logo.setObjectName("logo")
        pixmap = QPixmap("src/icons/material-symbols--bolt-outline.png")
        self.logo.setPixmap(pixmap)
        self.logo.setFixedSize(32, 32)
        self.logo.setScaledContents(True)

        self.title = QLabel("ForceBoard Metrics")
        self.title.setObjectName("title")

        self.title_spacer = QSpacerItem(
            40, 20,
            QSizePolicy.Expanding,
            QSizePolicy.Minimum
        )

        self.title_layout.addWidget(self.logo)
        self.title_layout.addWidget(self.title)
        self.title_layout.addItem(self.title_spacer)
        self.title_widget.setLayout(self.title_layout)

        # Board status
        self.balance_board = WiiBalanceBoard()
        self.balance_board_reader = BalanceBoardReader(self.balance_board)
        self.balance_board_reader.start()
        self.balanceboard_data = {
            "top_right": 0.0,
            "bottom_right": 0.0,
            "top_left": 0.0,
            "bottom_left": 0.0,
            "total_weight": 0.0
        }
        self.board_status_widget = BoardStatus(self.balance_board, self.balance_board_reader)
        self.board_status_widget.setObjectName("boardStatusWidget")
        self.balance_board_reader.connection_changed.connect(
            self.board_status_widget.on_connection_changed
        )

        # Tabs
        self.dashboard_widget = Dashboard(self.balance_board_reader)
        self.dashboard_widget.setObjectName("dashboardWidget")

        self.jump_test_widget = QWidget()
        self.jump_test_widget.setObjectName("jumpTestWidget")
        jump_test_layout = QVBoxLayout()
        jump_test_label = QLabel("Jump Test")
        jump_test_layout.addWidget(jump_test_label)
        self.jump_test_widget.setLayout(jump_test_layout)

        self.settings_widget = QWidget()
        self.settings_widget.setObjectName("settingsWidget")
        settings_layout = QVBoxLayout()
        settings_label = QLabel("Settings")
        settings_layout.addWidget(settings_label)
        self.settings_widget.setLayout(settings_layout)

        tabs = [
            (self.dashboard_widget, "Dashboard"),
            (self.jump_test_widget, "Jump Test"),
            (self.settings_widget, "Settings"),
        ]

        # Create the custom tabs
        self.navigation = CustomTabs(tabs=tabs, preset="horizontal_dark")
        self.navigation.set_stylesheet()

        # Primary layout
        primary_widget = QWidget()
        primary_layout = QVBoxLayout()
        primary_layout.addWidget(self.title_widget)
        primary_layout.addWidget(self.board_status_widget)
        primary_layout.addWidget(self.navigation)

        primary_widget.setLayout(primary_layout)
        self.setCentralWidget(primary_widget)

        self.apply_stylesheet()

    def apply_stylesheet(self):
        w = self.width()
        h = self.height()
        tab_min_width = max(160, int(w * 0.32))
        font_size = max(12, int(h * 0.03))

        style = f"""
        QMainWindow {{
            background-color: #000000; /* black background */
        }}

        QWidget#jumpTestWidget,
        QWidget#settingsWidget,
        QWidget#dashboardWidget {{
            background-color: #000000;
            border: 1px solid #888888; /* light gray thin border */
        }}

        QWidget#boardStatusWidget {{
            background-color: #000000;
            border: 1px solid #888888;
            height: 60px;
        }}

        QWidget#titleWidget {{
            background-color: #000000;
            border-bottom: 1px solid #888888;
        }}

        QLabel {{
            color: white;
            font-size: {font_size}px;
            font-weight: bold;
        }}

        QLabel#logo {{
            color: white;
        }}

        QPushButton {{
            background-color: #222222;
            color: white;
            border: 1px solid #888888;
            border-radius: 4px;
            padding: 2px 6px;
        }}

        QPushButton:hover {{
            background-color: #000000;
        }}
        """
        self.setStyleSheet(style)

    def resizeEvent(self, event):
        """Update dynamic sizes on window resize."""
        self.apply_stylesheet()
        super().resizeEvent(event)

    def update_balanceboard_values(self, data):
        self.balanceboard_data = data


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
