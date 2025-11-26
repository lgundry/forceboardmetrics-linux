from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal

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


class ConnectWindow(QDialog):
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
