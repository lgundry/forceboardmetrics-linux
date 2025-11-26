import struct
import subprocess
import sys
import time
import select
import bluetooth

from boards.board_interface import BoardInterface

BLUETOOTH_NAME = "Nintendo RVL-WBC-01"

# Wii Balance Board Constants
CONTINUOUS_REPORTING = 0x04
COMMAND_LIGHT = 0x11
COMMAND_REPORTING = 0x12
COMMAND_REQUEST_STATUS = 0x15
COMMAND_REGISTER = 0x16
COMMAND_READ_REGISTER = 0x17

INPUT_STATUS = 0x20
INPUT_READ_DATA = 0x21
EXTENSION_8BYTES = 0x32

# Balance Board Sensor Positions
TOP_RIGHT = 0
BOTTOM_RIGHT = 1
TOP_LEFT = 2
BOTTOM_LEFT = 3

# Constants
COMMAND_INTERVAL = 0.1


class WiiBalanceBoard(BoardInterface):
    def __init__(self, debug=False):
        self.calibration = [[0 for j in range(4)] for i in range(3)]
        self.calibration_requested = False
        self.light_state = False
        self.connected = False
        self.sock = None
        self.csock = None
        self.address = None
        self.debug = debug
        self.baseline_values = None

        try:
            self.sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            self.csock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        except ValueError:
            sys.exit(1)

    def setup_device(self, address:str | None = None) -> bool:
        if address is None:
            devices = bluetooth.discover_devices(duration=6, lookup_names=True)
            board_info = [
                (addr, name) for addr, name in devices if name == BLUETOOTH_NAME
            ]
            self.device_name = board_info[0][1]

            if not board_info:
                return False

            address = board_info[0][0]

        self.address = address

        # Start bluetoothctl in interactive mode
        process = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def send_bluetooth_command(cmd):
            process.stdin.write(cmd + "\n")
            process.stdin.flush()
            time.sleep(COMMAND_INTERVAL)

        try:
            # Remove existing device
            send_bluetooth_command(f"remove {address}")

            # Power on and start scanning
            send_bluetooth_command("power on")
            send_bluetooth_command("agent on")
            send_bluetooth_command("default-agent")

            # Start pairing process and immediately connect
            send_bluetooth_command(f"pair {address}")

            # Connect immediately
            send_bluetooth_command(f"connect {address}")

            # Trust device (can be done after connection)
            send_bluetooth_command(f"trust {address}")

            # Clean up
            send_bluetooth_command("quit")
            process.communicate()

            # Don't wait - return immediately to start the connection
            return True

        except Exception as e:
            process.terminate()
            return False

    def connect(self, address: str) -> bool:
        if address is None:
            return False

        try:
            # Connect to both channels
            self.sock.connect((address, 0x13))
            self.csock.connect((address, 0x11))
            self.connected = True

            # Register extension
            self._send_board_command(["00", COMMAND_REGISTER, "04", "A4", "00", "40", "00"])

            # Enable continuous reporting
            self._send_board_command(
                [COMMAND_REPORTING, CONTINUOUS_REPORTING, EXTENSION_8BYTES]
            )

            # Request calibration data
            self._request_calibration()

            # Turn on LED to indicate successful connection
            self.set_light(True)

            return True
        except Exception as e:
            self.disconnect()
            return False

    def set_light(self, on: bool) -> None:
        """Turn the power button LED on or off"""
        if on:
            val = "10"
        else:
            val = "00"
        self._send_board_command(["00", COMMAND_LIGHT, val])

    def disconnect(self) -> None:
        if self.connected:
            self.sock.close()
            self.csock.close()
            self.connected = False

    def _send_board_command(self, data):
        if not self.connected:
            return

        # Convert string hex values to integers if necessary
        cmd = [0x52]
        for item in data:
            if isinstance(item, str):
                cmd.append(int(item, 16))
            else:
                cmd.append(item)

        self.csock.send(bytes(cmd))
        time.sleep(0.1)

    def _request_calibration(self):
        self._send_board_command([COMMAND_READ_REGISTER, 0x04, 0xA4, 0x00, 0x24, 0x00, 0x18])
        self.calibration_requested = True

    def _parse_calibration(self, bytes_data):
        index = 0
        if len(bytes_data) == 16:
            for i in range(2):
                for j in range(4):
                    self.calibration[i][j] = struct.unpack(
                        ">H", bytes_data[index : index + 2]
                    )[0]
                    index += 2
        elif len(bytes_data) < 16:
            for i in range(4):
                self.calibration[2][i] = struct.unpack(
                    ">H", bytes_data[index : index + 2]
                )[0]
                index += 2

    def _calc_mass(self, raw, pos):
        """Calculate mass using simple linear scaling"""
        try:
            # Get calibration values for this sensor
            empty = self.calibration[0][pos]
            full = self.calibration[2][pos]

            # Apply zero calibration if available
            if self.baseline_values:
                raw = raw - self.baseline_values[pos]

            # Return 0 if reading is very low
            if raw <= 50:
                return 0.0

            # Check for valid calibration range
            if full <= empty or (full - empty) < 100:  # Added safety check
                return 0.0

            # Simple linear scaling: (raw - empty) / (full - empty) * 34kg
            weight = 34.0 * (raw - empty) / (full - empty)

            if weight < 3.0:
                return 0.0  # Ignore very low weights

            return weight

        except Exception as e:
            return 0.0

    def _process_data(self, data):
        if len(data) < 8:
            return None

        try:
            rawBL = (data[0] << 8) | data[1]
            rawTR = (data[2] << 8) | data[3]
            rawBR = (data[4] << 8) | data[5]
            rawTL = (data[6] << 8) | data[7]

            raw_values = [rawTR, rawBR, rawTL, rawBL]

            # Dynamic baseline check using calibration values
            baselines = [self.calibration[0][i] + 100 for i in range(4)]
            if all(raw <= base for raw, base in zip(raw_values, baselines)):
                return {
                    "top_right": 0.0,
                    "bottom_right": 0.0,
                    "top_left": 0.0,
                    "bottom_left": 0.0,
                    "total_weight": 0.0,
                }

            # Calculate masses using list comprehension
            positions = [TOP_RIGHT, BOTTOM_RIGHT, TOP_LEFT, BOTTOM_LEFT]
            masses = [
                self._calc_mass(raw, pos) for raw, pos in zip(raw_values, positions)
            ]

            total_mass = sum(masses)

            return {
                "top_right": masses[0],
                "bottom_right": masses[1],
                "top_left": masses[2],
                "bottom_left": masses[3],
                "total_weight": total_mass,
            }

        except Exception as e:
            return None

    def read_data(self) -> dict | None:
        if not self.connected:
            return None

        try:
            # Set socket timeout to prevent blocking
            data = self.sock.recv(25)

            if not data or len(data) < 2:
                return None

            data_type = data[1]

            if data_type == INPUT_STATUS:
                self._send_board_command(
                    [COMMAND_REPORTING, CONTINUOUS_REPORTING, EXTENSION_8BYTES]
                )
            elif data_type == INPUT_READ_DATA:
                if self.calibration_requested:
                    packet_length = (data[4] >> 4) + 1
                    self._parse_calibration(data[7 : 7 + packet_length])
                    if packet_length < 16:
                        self.calibration_requested = False
            elif data_type == EXTENSION_8BYTES:
                return self._process_data(data[2:12])

        except bluetooth.btcommon.BluetoothError as e:
            if str(e) != "timed out":
                if self.debug:
                    print(f"\nBluetooth error: {e}")
        except Exception as e:
            if self.debug:
                print(f"\nError reading data: {e}")

        return None

    def calibrate_zero(self) -> bool:
        time.sleep(1)

        readings = []
        for _ in range(5):
            data = self.read_data()
            if data:
                readings.append(
                    [
                        data["top_right"],
                        data["bottom_right"],
                        data["top_left"],
                        data["bottom_left"],
                    ]
                )
            time.sleep(0.1)

        if readings:
            # Average the readings for each sensor
            self.baseline_values = [sum(col) / len(readings) for col in zip(*readings)]
            return True
        return False
