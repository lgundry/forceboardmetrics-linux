import struct
import time

import bluetooth

CONTROL = 0x13
DATA = 0x11


def find_balance_board():
    print(">> Scanning for nearby Bluetooth devices...")
    nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True)
    found = False
    for addr, name in nearby_devices:
        print(f"Found device: {name} [{addr}]")
        if "Nintendo" in name or "Balance Board" in name:
            print(">> This appears to be a Balance Board!")
            found = True
    if not found:
        print(
            ">> No Balance Board found. Make sure it's in sync mode (red button pressed)."
        )
    return None  # Don't try to connect yet


def connect_board(addr):
    print(
        f">> Connecting to CONTROL (0x{CONTROL:02X}) and DATA (0x{DATA:02X}) channels..."
    )
    ctl_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    ctl_sock.connect((addr, CONTROL))
    print(">> CONTROL channel connected.")

    data_sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    data_sock.connect((addr, DATA))
    print(">> DATA channel connected.")
    return ctl_sock, data_sock


def wii_init_sequence(ctl_sock, data_sock):
    """
    Following the exact Wii initialization sequence from the documentation.
    """
    print(">> Starting Wii initialization sequence...")

    # Step 1: Initialize without encryption
    print(">> Sending initialization commands...")
    ctl_sock.send(bytes([0xF0, 0x55]))  # Standard extension init
    time.sleep(0.1)
    ctl_sock.send(bytes([0xFB, 0x00]))  # Disable encryption
    time.sleep(0.1)

    # Step 2: Read extension identifier (should be 0x0402)
    print(">> Attempting to read extension ID...")
    try:
        data_sock.settimeout(0.1)
        ctl_sock.send(bytes([0x00]))  # Request status
        data = data_sock.recv(21)  # Read status report
        print(f">> Status data: {data.hex()}")
    except bluetooth.btcommon.BluetoothError:
        print(">> No status data (continuing)")

    # Step 3: Send calibration commands
    print(">> Sending calibration sequence...")
    for _ in range(3):  # Send F1 AA three times
        ctl_sock.send(bytes([0xF1, 0xAA]))
        time.sleep(0.1)

    # Send the magic calibration sequence
    ctl_sock.send(bytes([0xF1, 0xAA, 0xAA, 0x55, 0xAA, 0xAA, 0xAA]))
    time.sleep(0.1)
    ctl_sock.send(bytes([0xF1, 0xAA]))
    time.sleep(1.0)  # Longer wait after calibration

    # Step 4: Read calibration data
    print(">> Reading calibration data...")
    try:
        # Request memory read from 0x20-0x3F
        ctl_sock.send(bytes([0x17, 0x00, 0x20, 0x00, 0x20]))
        time.sleep(0.1)
        data_sock.settimeout(1.0)
        calib = data_sock.recv(32)
        if calib:
            print(f">> Raw calibration: {calib.hex()}")
        else:
            print(">> No calibration data received")
    except bluetooth.btcommon.BluetoothError as e:
        print(f">> Error reading calibration: {e}")

    print(">> Initialization complete")


def enable_reporting(ctl_sock, retries=6):
    print(">> Sending continuous sensor reporting (0x32)...")
    for i in range(retries):
        ctl_sock.send(bytes([0x52, 0x12, 0x00, 0x32]))
        print(f">> Reporting command sent [{i+1}/{retries}]")
        time.sleep(0.1)


def parse_data(data):
    """
    Parse 0x32 report: 8 bytes for four 16-bit sensors
    Byte order: TR, BR, TL, BL (big-endian)
    """
    if len(data) < 9:
        return None
    tr, br, tl, bl = struct.unpack(">HHHH", data[1:9])
    total = tr + br + tl + bl
    x = ((tr + br) - (tl + bl)) / total if total != 0 else 0
    y = ((tl + tr) - (bl + br)) / total if total != 0 else 0
    return total, x, y, (tl, tr, bl, br)


if __name__ == "__main__":
    try:
        addr = find_balance_board()
        if not addr:
            print(">> Balance Board not found.")
            exit(1)

        ctl_sock, data_sock = connect_board(addr)
        wii_init_sequence(ctl_sock, data_sock)
        enable_reporting(ctl_sock)

        print(">> Starting data reception...")
        data_sock.settimeout(1.0)

        while True:
            try:
                data = data_sock.recv(32)  # Read enough for a full report
                if data and len(data) >= 8:
                    result = parse_data(data)
                    if result:
                        total, x, y, sensors = result
                        print(f"Weight: {total/100:.2f}kg, X: {x:.2f}, Y: {y:.2f}")
                time.sleep(0.01)  # Small delay to prevent busy-waiting
            except bluetooth.btcommon.BluetoothError as e:
                if "timed out" not in str(e):
                    print(f">> Error: {e}")
                    break
    except KeyboardInterrupt:
        print("\n>> Shutting down...")
    finally:
        try:
            ctl_sock.close()
            data_sock.close()
        except Exception as e:
            print(f">> Error during cleanup: {e}")

    print(">> Entering main loop: printing all raw data...")
    try:
        while True:
            try:
                data = data_sock.recv(25)
                print(f">> Raw data: {data.hex()}")
            except bluetooth.btcommon.BluetoothError as e:
                print(f">> Bluetooth error during recv: {e}")
                continue

            parsed = parse_data(data)
            if parsed:
                total, x, y, sensors = parsed
                print(
                    f">> Total: {total} | X: {x:.2f} | Y: {y:.2f} | Sensors: {sensors}"
                )

            time.sleep(0.05)  # avoid flooding the board
    except KeyboardInterrupt:
        print(">> Exiting...")
    finally:
        ctl_sock.close()
        data_sock.close()
