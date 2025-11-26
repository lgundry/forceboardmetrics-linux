from PySide6.QtCore import QThread, Signal
import time

class BalanceBoardReader(QThread):
    data_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, board):
        super().__init__()
        self.board = board
        self._running = False
        self._last_connection = None

    def run(self):
        self._running = True
        while self._running:
            connected = self.board.connected
            if connected != self._last_connection:
                self.connection_changed.emit(connected)
                self._last_connection = connected

            if connected:
                data = self.board.read_data() or {
                    "top_left": 0.0,
                    "top_right": 0.0,
                    "bottom_left": 0.0,
                    "bottom_right": 0.0,
                    "total_weight": 0.0
                }
            else:
                data = {
                    "top_left": 0.0,
                    "top_right": 0.0,
                    "bottom_left": 0.0,
                    "bottom_right": 0.0,
                    "total_weight": 0.0
                }

            self.data_received.emit(data)
            time.sleep(0.01)

    def stop(self):
        self._running = False
        self.wait()
