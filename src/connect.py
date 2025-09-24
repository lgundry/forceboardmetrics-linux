import subprocess
import sys
import time

import bluetooth

from data_proc import calibrate_sensors, process_sensor_data

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


class BoardConnection:
    def __init__(self, debug=False):
        self.calibration = [[0 for j in range(4)] for i in range(3)]
        self.calibration_requested = False
        self.light_state = False
        self.connected = False
        self.sock = None
        self.csock = None
        self.address = None
        self.debug = debug

        try:
            self.sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
            self.csock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
        except ValueError:
            print("Error: Bluetooth not found")
            sys.exit(1)

    def setup_device(self, address=None):
        """Handle device discovery and pairing"""
        if address is None:
            print("Discovering balance board...")
            print("Press the red sync button on the Balance Board now")
            devices = bluetooth.discover_devices(duration=6, lookup_names=True)
            board_info = [
                (addr, name) for addr, name in devices if name == BLUETOOTH_NAME
            ]

            if not board_info:
                print("No Balance Board found.")
                return False

            address = board_info[0][0]
            print(f"Found Balance Board at {address}")

        self.address = address

        print("Starting Bluetooth setup...")
        process = subprocess.Popen(
            ["bluetoothctl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        def send_command(cmd):
            process.stdin.write(cmd + "\n")
            process.stdin.flush()
            time.sleep(0.25)

        try:
            send_command(f"remove {address}")
            send_command("power on")
            send_command("agent on")
            send_command("default-agent")
            send_command(f"pair {address}")
            time.sleep(0.5)
            send_command(f"connect {address}")
            time.sleep(0.5)
            send_command(f"trust {address}")
            send_command("quit")
            process.communicate()
            return True

        except Exception as e:
            print(f"Error during setup: {e}")
            process.terminate()
            return False

    def connect(self):
        """Establish connection to the board"""
        try:
            self.sock.connect((self.address, 0x13))
            self.csock.connect((self.address, 0x11))
            self.connected = True

            # Initialize the board
            self._send_command(["00", COMMAND_REGISTER, "04", "A4", "00", "40", "00"])
            time.sleep(0.25)

            self._send_command(
                [COMMAND_REPORTING, CONTINUOUS_REPORTING, EXTENSION_8BYTES]
            )
            time.sleep(0.25)

            self._request_calibration()
            time.sleep(0.25)

            self.set_light(True)
            return True

        except Exception as e:
            print(f"\nConnection failed: {e}")
            self.disconnect()
            return False

    def _send_command(self, data):
        """Send command to the board"""
        if not self.connected:
            return
        cmd = [0x52]
        for item in data:
            if isinstance(item, str):
                cmd.append(int(item, 16))
            else:
                cmd.append(item)
        self.csock.send(bytes(cmd))
        time.sleep(0.1)

    def _request_calibration(self):
        """Request calibration data from the board"""
        self._send_command([COMMAND_READ_REGISTER, 0x04, 0xA4, 0x00, 0x24, 0x00, 0x18])
        self.calibration_requested = True

    def set_light(self, on):
        """Control the board's LED"""
        val = "10" if on else "00"
        self._send_command(["00", COMMAND_LIGHT, val])

    def read_data(self):
        """Read raw data from the board"""
        if not self.connected:
            return None

        try:
            self.sock.settimeout(0.01)
            data = self.sock.recv(25)

            if not data or len(data) < 2:
                return None

            data_type = data[1]

            if data_type == INPUT_STATUS:
                self._send_command(
                    [COMMAND_REPORTING, CONTINUOUS_REPORTING, EXTENSION_8BYTES]
                )
            elif data_type == INPUT_READ_DATA:
                if self.calibration_requested:
                    packet_length = (data[4] >> 4) + 1
                    calibrate_sensors(data[7 : 7 + packet_length], self.calibration)
                    if packet_length < 16:
                        self.calibration_requested = False
            elif data_type == EXTENSION_8BYTES:
                return process_sensor_data(data[2:12], self.calibration)

        except bluetooth.btcommon.BluetoothError as e:
            if str(e) != "timed out":
                print(f"\nBluetooth error: {e}")
        except Exception as e:
            print(f"\nError reading data: {e}")

        return None

    def disconnect(self):
        """Close the connection"""
        if self.connected:
            self.sock.close()
            self.csock.close()
            self.connected = False

    def _get_raw_data(self):
        """Get raw sensor data for debugging"""
        try:
            data = self.sock.recv(25)
            if data and len(data) > 3:
                return {
                    "tr": (data[0] << 8) | data[1],
                    "br": (data[2] << 8) | data[3],
                    "tl": (data[4] << 8) | data[5],
                    "bl": (data[6] << 8) | data[7],
                }
        except Exception:
            pass
        return None
