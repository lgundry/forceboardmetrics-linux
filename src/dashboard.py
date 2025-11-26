from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class Dashboard(QWidget):
    def __init__(self, balance_board_reader, parent=None):
        super().__init__(parent)
        self.reader = balance_board_reader

        layout = QVBoxLayout()
        
        self.sensor_label = QLabel("Board not connected")
        self.sensor_label.setAlignment(Qt.AlignCenter)
        self.sensor_label.setStyleSheet("font-size: 16px;")

        layout.addWidget(self.sensor_label)
        self.setLayout(layout)

        # Connect to reader signals
        self.reader.data_received.connect(self.update_sensor_data)

    def update_sensor_data(self, data):
        """Update dashboard whenever new data is received"""
        text = (
            f"Top Left: {data['top_left']:.1f} kg\n"
            f"Top Right: {data['top_right']:.1f} kg\n"
            f"Bottom Left: {data['bottom_left']:.1f} kg\n"
            f"Bottom Right: {data['bottom_right']:.1f} kg\n"
            f"Total: {data['total_weight']:.1f} kg"
        )
        self.sensor_label.setText(text)

    def set_reader(self, reader):
        self.reader = reader
        self.reader.data_received.connect(self.update_sensor_data)
