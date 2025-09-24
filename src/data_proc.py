import struct


def calibrate_sensors(bytes_data, calibration):
    """Process calibration data from the board"""
    index = 0
    if len(bytes_data) == 16:
        for i in range(2):
            for j in range(4):
                calibration[i][j] = struct.unpack(">H", bytes_data[index : index + 2])[
                    0
                ]
                index += 2
    elif len(bytes_data) < 16:
        for i in range(4):
            calibration[2][i] = struct.unpack(">H", bytes_data[index : index + 2])[0]
            index += 2


def calculate_mass(raw, calibration_empty, calibration_full):
    """Calculate mass using simple linear scaling"""
    try:
        if (
            calibration_full <= calibration_empty
            or (calibration_full - calibration_empty) < 100
        ):
            return 0.0

        # Simple linear scaling: (raw - empty) / (full - empty) * 34kg
        weight = (
            34.0 * (raw - calibration_empty) / (calibration_full - calibration_empty)
        )

        return 0.0 if weight < 3.0 else weight

    except Exception as e:
        print(f"\nError calculating mass: {e}")
        return 0.0


def process_sensor_data(data, calibration):
    """Process raw sensor data into weight measurements"""
    if len(data) < 8:
        return None

    try:
        # Extract raw values
        rawBL = (data[0] << 8) | data[1]
        rawTR = (data[2] << 8) | data[3]
        rawBR = (data[4] << 8) | data[5]
        rawTL = (data[6] << 8) | data[7]

        raw_values = [rawTR, rawBR, rawTL, rawBL]

        # Check if board is empty
        baselines = [calibration[0][i] + 100 for i in range(4)]
        if all(raw <= base for raw, base in zip(raw_values, baselines)):
            return {
                "top_right": 0.0,
                "bottom_right": 0.0,
                "top_left": 0.0,
                "bottom_left": 0.0,
                "total_weight": 0.0,
            }

        # Calculate masses for each sensor
        masses = [
            calculate_mass(raw, calibration[0][i], calibration[2][i])
            for i, raw in enumerate(raw_values)
        ]

        return {
            "top_right": masses[0],
            "bottom_right": masses[1],
            "top_left": masses[2],
            "bottom_left": masses[3],
            "total_weight": sum(masses),
        }

    except Exception as e:
        print(f"\nError processing sensor data: {e}")
        return None
