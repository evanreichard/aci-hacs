from enum import Enum


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
