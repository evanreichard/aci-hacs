from dataclasses import dataclass
from .models import DeviceMode, RampStatus


@dataclass
class AutoState():
    high_temp_on: bool
    low_temp_on: bool
    high_temp: int
    low_temp: int


@dataclass
class CycleState():
    cycle_on_time: int
    cycle_off_time: int


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

    def get_cycle_state(self) -> CycleState | None:
        if self.cycle_off_time is None or self.cycle_on_time is None:
            return None
        return CycleState(self.cycle_on_time, self.cycle_off_time)

    def get_auto_state(self) -> AutoState | None:
        if (self.auto_high_temp is None or self.auto_high_temp_on is None or
                self.auto_low_temp is None or self.auto_low_temp_on is None):
            return None
        return AutoState(
            high_temp_on=self.auto_high_temp_on,
            low_temp_on=self.auto_low_temp_on,
            high_temp=self.auto_high_temp,
            low_temp=self.auto_low_temp
        )

    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if hasattr(value, 'value'):
                result[key] = str(value)
            else:
                result[key] = value
        return result
