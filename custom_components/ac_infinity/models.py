from enum import Enum
from dataclasses import dataclass


class DeviceNotSupported(Exception):
    """Raised when device type is not supported"""
    pass


class DeviceType(Enum):
    AIRTAP = (6, "D", "AirTap")

    prefix: str
    model: str

    def __new__(cls, value, prefix, display_name):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.prefix = prefix
        obj.model = display_name
        return obj

    def __str__(self):
        return self.model


class DeviceMode(Enum):
    OFF = (1, "Off")
    ON = (2, "On")
    AUTO_TEMP = (3, "Auto")
    TIMER_TO_ON = (4, "Timer to On")
    TIMER_TO_OFF = (5, "Timer to Off")
    CYCLE = (6, "Cycle")

    id_string: str

    def __new__(cls, id: int, id_string: str):
        obj = object.__new__(cls)
        obj._value_ = id
        obj.id_string = id_string
        return obj

    def __str__(self):
        return self.id_string

    @classmethod
    def from_string(cls, id_string: str):
        for mode in cls:
            if mode.id_string == id_string:
                return mode
        raise ValueError(f"No DeviceMode with id_string '{id_string}'")


class RampStatus(Enum):
    UP = 8
    DOWN = 4
    NONE = 0


@dataclass
class ParsedAdvertisement:
    id: str
    """
    The device ID (e.g. "D-S40BM")
    """

    name: str
    """
    # The device name (e.g. "AirTap (D-S40BM)")
    """

    model: str
    """
    The device model (e.g. "AirTap")
    """

    fan_speed: int
    """
    The device fan speed (e.g. 0 - 10)
    """

    temperature: float
    """
    # The device temperature (e.g. 14.85)
    """


@dataclass
class ParsedStatus:
    temperature: float
    """
    The device temperature (e.g. 14.85)
    """

    fan_speed: int
    """
    The device fan speed (e.g. 0 - 10)
    """

    ramp_status: RampStatus
    """
    The device ramp status (e.g. UP, DOWN, NONE)
    """

    mode: DeviceMode
    """
    The device mode (e.g. OFF, ON, AUTO_TEMP, TIMER_TO_ON, TIMER_TO_OFF, CYCLE)
    """
