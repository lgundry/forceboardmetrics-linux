import struct
import subprocess
import sys
import time

import bluetooth

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


class BalanceBoard:
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
            print("Error: Bluetooth not found")
            sys.exit(1)

    def setup_device(self, address=None):
        """Handle device discovery, pairing, and connection"""
        if address is None:
            print("Discovering balance board...")
            print("Press the red sync button on the back of your Balance Board now")
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

        # Start bluetoothctl in interactive mode
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
            # Remove existing device
            print("Removing any existing pairing...")
            send_command(f"remove {address}")

            # Power on and start scanning
            send_command("power on")
            send_command("agent on")
            send_command("default-agent")

            # Start pairing process and immediately connect
            print("Starting pairing and connection process...")
            send_command(f"pair {address}")
            time.sleep(0.5)

            # Connect immediately
            print("Connecting...")
            send_command(f"connect {address}")
            time.sleep(0.5)

            # Trust device (can be done after connection)
            print("Setting up trust...")
            send_command(f"trust {address}")

            # Clean up
            send_command("quit")
            process.communicate()

            # Don't wait - return immediately to start the connection
            print("Bluetooth setup completed - connecting to board...")
            return True

        except Exception as e:
            print(f"Error during setup: {e}")
            process.terminate()
            return False

    def connect(self, address):
        if address is None:
            print("No device specified")
            return False

        print(f"Connecting to {address}...")
        try:
            # Connect to both channels
            self.sock.connect((address, 0x13))
            self.csock.connect((address, 0x11))
            self.connected = True

            # Initialize the board
            print("Initializing board...", end="", flush=True)

            # Register extension
            self._send_command(["00", COMMAND_REGISTER, "04", "A4", "00", "40", "00"])
            time.sleep(0.25)
            print(".", end="", flush=True)

            # Enable continuous reporting
            self._send_command(
                [COMMAND_REPORTING, CONTINUOUS_REPORTING, EXTENSION_8BYTES]
            )
            time.sleep(0.25)
            print(".", end="", flush=True)

            # Request calibration data
            self._request_calibration()
            time.sleep(0.25)
            print(".", end="", flush=True)

            # Turn on LED to indicate successful connection
            self.set_light(True)
            print(" done!")

            return True
        except Exception as e:
            print(f"\nConnection failed: {e}")
            self.disconnect()
            return False

    def set_light(self, on):
        """Turn the power button LED on or off"""
        if on:
            val = "10"
        else:
            val = "00"
        self._send_command(["00", COMMAND_LIGHT, val])
        time.sleep(0.5)

    def disconnect(self):
        if self.connected:
            self.sock.close()
            self.csock.close()
            self.connected = False

    def _send_command(self, data):
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
        self._send_command([COMMAND_READ_REGISTER, 0x04, 0xA4, 0x00, 0x24, 0x00, 0x18])
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
            print(f"\nError calculating mass: {e}")
            return 0.0

    def _process_data(self, data):
        if len(data) < 8:  # We need at least 8 bytes for the sensors
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

            # Apply a moving average filter if total weight has changed significantly
            if hasattr(self, "_last_total") and abs(total_mass - self._last_total) > 5:
                total_mass = 0.7 * self._last_total + 0.3 * total_mass
            self._last_total = total_mass

            return {
                "top_right": masses[0],
                "bottom_right": masses[1],
                "top_left": masses[2],
                "bottom_left": masses[3],
                "total_weight": total_mass,
            }

        except Exception as e:
            print(f"\nError processing sensor data: {e}")
            return None

    def read_data(self):
        if not self.connected:
            return None

        try:
            # Set socket timeout to prevent blocking
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
                    self._parse_calibration(data[7 : 7 + packet_length])
                    if packet_length < 16:
                        self.calibration_requested = False
            elif data_type == EXTENSION_8BYTES:
                return self._process_data(data[2:12])

        except bluetooth.btcommon.BluetoothError as e:
            if str(e) != "timed out":
                print(f"\nBluetooth error: {e}")
        except Exception as e:
            print(f"\nError reading data: {e}")

        return None

    def calibrate_zero(self):
        """Take initial reading to establish zero baseline"""
        print("\nCalibrating zero baseline - keep board empty...")
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
            print("Zero calibration complete!")
            return True
        return False


def main():
    # Enable debug mode with --debug flag
    debug_mode = "--debug" in sys.argv
    board = BalanceBoard(debug=debug_mode)

    # Get board address if provided
    board_addr = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            board_addr = arg
            break

    print("Balance Board Setup")
    print("==================")

    print("Press the red sync button on the Balance Board now,")
    print("then wait for the discovery process...")
    print("DO NOT STEP ON BOARD")

    if not board.setup_device(board_addr):
        print("Failed to set up the Balance Board")
        sys.exit(1)

    # Connect immediately after setup
    print("Establishing connection...")
    if not board.connect(board.address):
        print("Failed to connect to Balance Board")
        sys.exit(1)

    print("Balance Board connected!")
    print("Performing initial calibration...")

    if not board.calibrate_zero():
        print("Failed to calibrate zero point")
        board.disconnect()
        sys.exit(1)

    print("Step on the board to begin measuring...")
    print("Press Ctrl+C to exit\n")

    try:
        last_weight = 0
        weight_history = []  # For smoothing
        display_threshold = 0.1  # Only display changes above this threshold

        while True:
            data = board.read_data()
            if data:
                weight = data["total_weight"]
                weight_history.append(weight)

                # Keep last 3 measurements for smoothing
                if len(weight_history) > 3:
                    weight_history.pop(0)

                # Apply smoothing
                smoothed_weight = sum(weight_history) / len(weight_history)

                # Only print if weight changed significantly
                if abs(smoothed_weight - last_weight) > display_threshold:
                    print(
                        f"\rWeight: {smoothed_weight:.1f} kg | "
                        f"TR: {data['top_right']:.1f} "
                        f"TL: {data['top_left']:.1f} "
                        f"BR: {data['bottom_right']:.1f} "
                        f"BL: {data['bottom_left']:.1f}" + " " * 20,
                        end="",
                    )  # Fixed typo here
                    last_weight = smoothed_weight

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        board.disconnect()


if __name__ == "__main__":
    main()
