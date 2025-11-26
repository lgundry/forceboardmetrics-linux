from abc import ABC, abstractmethod

class BoardInterface(ABC):
    """
    Abstract interface for any force-sensing board.
    All concrete board classes must implement these methods.
    """

    @abstractmethod
    def setup_device(self, address=None) -> bool:
        """
        Discover, pair, or otherwise prepare the device for connection.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def connect(self, address) -> bool:
        """
        Establish connection to the board.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def calibrate_zero(self) -> bool:
        """
        Calibrate the zero baseline for the sensors.
        Returns True if successful.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        Disconnect from the board and clean up resources.
        """
        pass

    @abstractmethod
    def read_data(self) -> dict | None:
        """
        Read the current sensor values from the board.
        Must return a dictionary like:
        {
            "top_right": float,
            "bottom_right": float,
            "top_left": float,
            "bottom_left": float,
            "total_weight": float
        }
        Return None if no valid data is available.
        """
        pass

    @abstractmethod
    def set_light(self, on: bool):
        """
        Turn the board's indicator light on or off if available.
        """
        pass
