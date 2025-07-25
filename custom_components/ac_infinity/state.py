from dataclasses import dataclass
from .models import DeviceMode, ParsedAdvertisement, ParsedStatus, RampStatus


@dataclass
class ACIDeviceState:
    # Core Identity (Advertisement Only)
    id: str | None = None
    name: str | None = None
    model: str | None = None

    # Operational Data (Advertisement & Characteristic)
    temperature: float | None = None
    fan_speed: int | None = None
    fan_speed_on: int | None = None
    fan_speed_off: int | None = None

    # Extended Operational Data (Characteristic & Model Info)
    mode: DeviceMode | None = None
    ramp_status: RampStatus | None = None
    auto_high_temp: int | None = None
    auto_high_temp_on: bool | None = None
    auto_low_temp: int | None = None
    auto_low_temp_on: bool | None = None
    cycle_off_time: int | None = None
    cycle_on_time: int | None = None

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if hasattr(value, 'value'):
                result[key] = str(value)
            else:
                result[key] = value
        return result
