from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, 
    QSpacerItem, QStackedLayout, QPushButton, QDialog, QTextEdit,
)
from boards.connect import ConnectWindow
from boards.balance_board_reader import BalanceBoardReader

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QSpacerItem,
    QSizePolicy, QStackedLayout
)
from boards.balance_board_reader import BalanceBoardReader
from boards.connect import ConnectWindow

class BoardStatus(QWidget):
    def __init__(self, balance_board, reader: BalanceBoardReader = None, parent=None):
        super().__init__(parent)
        self.balance_board = balance_board
        self.is_connected = False
        self.reader = reader

        # Set a fixed height for compact display
        self.setFixedHeight(60)

        self.setObjectName("boardStatus")

        # Load WiFi icons
        self.icon_red = QPixmap("src/icons/material-symbols--android-wifi-3-bar(2).png")
        self.icon_green = QPixmap("src/icons/material-symbols--android-wifi-3-bar(3).png")

        # Status icon label
        self.board_status_icon_widget = QLabel()
        self.board_status_icon_widget.setFixedSize(32, 32)
        self.board_status_icon_widget.setScaledContents(True)
        self.board_status_icon_widget.setAlignment(Qt.AlignCenter)
        self.board_status_icon_widget.setPixmap(self.icon_red)

        # Board info
        self.board_name_label_widget = QLabel("No board connected")
        self.board_name_label_widget.setObjectName("boardName")
        self.board_connection_status_label_widget = QLabel("Press Connect to connect to board")
        self.board_connection_status_label_widget.setObjectName("boardSubtitle")

        self.connection_status_widget = QWidget()
        self.connection_status_layout = QVBoxLayout()
        self.connection_status_layout.setContentsMargins(0, 0, 0, 0)
        self.connection_status_layout.setSpacing(2)
        self.connection_status_layout.addWidget(self.board_name_label_widget)
        self.connection_status_layout.addWidget(self.board_connection_status_label_widget)
        self.connection_status_widget.setLayout(self.connection_status_layout)

        self.board_status_spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Battery / Connect button stacked layout
        self.battery_label_widget = QLabel("0% battery")
        self.battery_label_widget.setAlignment(Qt.AlignCenter)

        self.connect_button = QPushButton("Connect")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.connect_button.clicked.connect(self.connect_to_board)

        self.battery_connect_button_widget = QWidget()
        self.battery_connect_button_layout = QStackedLayout()
        self.battery_connect_button_layout.setContentsMargins(0, 0, 0, 0)
        self.battery_connect_button_layout.addWidget(self.battery_label_widget)
        self.battery_connect_button_layout.addWidget(self.connect_button)
        self.battery_connect_button_layout.setCurrentWidget(self.connect_button)
        self.battery_connect_button_widget.setLayout(self.battery_connect_button_layout)
        self.battery_connect_button_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Root layout
        self.root_layout = QHBoxLayout()
        self.root_layout.setContentsMargins(8, 4, 8, 4)
        self.root_layout.setSpacing(8)
        self.root_layout.addWidget(self.board_status_icon_widget)
        self.root_layout.addWidget(self.connection_status_widget)
        self.root_layout.addItem(self.board_status_spacer)
        self.root_layout.addWidget(self.battery_connect_button_widget)
        self.setLayout(self.root_layout)

        self.apply_stylesheet()

    def on_connection_changed(self, connected: bool):
        self.is_connected = connected
        if connected:
            self.board_name_label_widget.setText(getattr(self.balance_board, "device_name", "Board"))
            self.board_connection_status_label_widget.setText("Connected")
            self.board_status_icon_widget.setPixmap(self.icon_green)
            self.battery_connect_button_layout.setCurrentWidget(self.battery_label_widget)
        else:
            self.board_name_label_widget.setText("No board connected")
            self.board_connection_status_label_widget.setText("Disconnected")
            self.board_status_icon_widget.setPixmap(self.icon_red)
            self.battery_connect_button_layout.setCurrentWidget(self.connect_button)
            self.battery_label_widget.setText("0% battery")

    def update_battery_and_status(self, data: dict):
        if self.is_connected:
            battery = getattr(self.balance_board, "battery_level", 0)
            self.battery_label_widget.setText(f"{battery}% battery")

    def connect_to_board(self):
        def on_finish(success):
            if success:
                if not self.reader:
                    self.reader = BalanceBoardReader(self.balance_board)
                    self.reader.start()
                self.set_reader(self.reader)

        self.connect_window = ConnectWindow(self.balance_board)
        self.connect_window.worker.finished.connect(on_finish)
        self.connect_window.show()

    def apply_stylesheet(self):
        stylesheet = """
            QWidget#boardStatus {
                background-color: #000000;
                border: 1px solid #888888;
                border-radius: 6px;
            }
            QLabel#boardName {
                font-weight: bold;
                font-size: 12px;
                color: #FFFFFF;
            }
            QLabel#boardSubtitle {
                font-size: 10px;
                color: #CCCCCC;
            }
            QLabel {
                font-size: 11px;
            }
            QPushButton#connectButton {
                padding: 4px 10px;
                font-size: 11px;
                border-radius: 6px;
                border: 1px solid #888888;
                background-color: #222222;
                color: white;
            }
            QPushButton#connectButton:hover {
                background-color: #000000;
            }
        """
        self.setStyleSheet(stylesheet)



class ConnectWorker(QThread):
    log = Signal(str)
    finished = Signal(bool)

    def __init__(self, board, board_addr=None):
        super().__init__()
        self.board = board
        self.board_addr = board_addr

    def run(self):
        board = self.board

        def log(msg):
            self.log.emit(msg)

        log("Balance Board Setup")
        log("===================")
        log("Press the red sync button on the Balance Board now,")
        log("then wait for the discovery process...")
        log("DO NOT STEP ON BOARD\n")

        if not board.setup_device(self.board_addr):
            log("Failed to set up the Balance Board")
            self.finished.emit(False)
            return

        log("Establishing connection...")
        if not board.connect(board.address):
            log("Failed to connect to Balance Board")
            self.finished.emit(False)
            return

        log("Connected!")
        log("Calibrating zero point...")

        if not board.calibrate_zero():
            log("Failed to calibrate zero point")
            board.disconnect()
            self.finished.emit(False)
            return

        log("Calibration successful.")
        log("Step on the board to begin measuring.\n")

        self.finished.emit(True)
    
    def set_dashboard(self, dashboard_widget):
        self.dashboard_widget = dashboard_widget

class ConnectWindow(QDialog):
    finished_connection = Signal(bool)  # Emit connection result to caller

    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.board = board

        self.setWindowTitle("Connect to Balance Board")
        self.resize(500, 400)

        layout = QVBoxLayout()

        self.instructions = QLabel(
            "This will guide you through connecting your Balance Board."
        )
        layout.addWidget(self.instructions)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        self.close_button = QPushButton("Close")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

        # Start worker
        self.worker = ConnectWorker(board)
        self.worker.log.connect(self.append_output)
        self.worker.finished.connect(self.finish)
        self.worker.start()

    def append_output(self, text):
        self.output.append(text)

    def finish(self, success):
        if success:
            self.output.append("\nConnection Successful!")
        else:
            self.output.append("\nConnection Failed.")

        self.close_button.setEnabled(True)
        self.finished_connection.emit(success)
