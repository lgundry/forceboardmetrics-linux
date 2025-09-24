import sys

from connect import BoardConnection


def main():
    # Enable debug mode with --debug flag
    debug_mode = "--debug" in sys.argv
    board = BoardConnection(debug=debug_mode)

    # Get board address if provided
    board_addr = None
    for arg in sys.argv[1:]:
        if not arg.startswith("--"):
            board_addr = arg
            break

    if not board.setup_device(board_addr):
        print("Failed to set up the Balance Board")
        sys.exit(1)

    if not board.connect():
        print("Failed to connect to Balance Board")
        sys.exit(1)

    print("Balance Board connected!")
    print("Step on the board to begin measuring...")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            data = board.read_data()
            if data:
                print(
                    f"\rWeight: {data['total_weight']:.1f} kg | "
                    f"TR: {data['top_right']:.1f} "
                    f"TL: {data['top_left']:.1f} "
                    f"BR: {data['bottom_right']:.1f} "
                    f"BL: {data['bottom_left']:.1f} | ",
                    end="",
                )

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        board.disconnect()


if __name__ == "__main__":
    main()
