from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from connect import BoardConnection


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Force Board Metrics")
        self.setMinimumSize(400, 300)

        # Initialize board connection
        self.board = BoardConnection()
        self.setup_ui()
        self.setup_board()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Create labels for displaying data
        self.weight_label = QLabel("Weight: 0.0 kg")
        self.sensors_label = QLabel("Sensors: TR: 0.0 TL: 0.0 BR: 0.0 BL: 0.0")
        self.status_label = QLabel("Status: Disconnected")

        layout.addWidget(self.weight_label)
        layout.addWidget(self.sensors_label)
        layout.addWidget(self.status_label)

        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(100)  # Update every 100ms

    def setup_board(self):
        if not self.board.setup_device():
            self.status_label.setText("Status: Setup Failed")
            return

        if not self.board.connect():
            self.status_label.setText("Status: Connection Failed")
            return

        self.status_label.setText("Status: Connected")

    def update_data(self):
        data = self.board.read_data()
        if data:
            self.weight_label.setText(f"Weight: {data['total_weight']:.1f} kg")
            self.sensors_label.setText(
                f"Sensors: "
                f"TR: {data['top_right']:.1f} "
                f"TL: {data['top_left']:.1f} "
                f"BR: {data['bottom_right']:.1f} "
                f"BL: {data['bottom_left']:.1f}"
            )

    def closeEvent(self, event):
        self.board.disconnect()
        event.accept()


def main():
    app = QApplication([])

    # Load stylesheet
    with open("src/style.qss", "r") as f:
        app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
