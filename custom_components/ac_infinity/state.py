from dataclasses import dataclass
from .models import DeviceMode, ParsedAdvertisement, ParsedStatus, RampStatus


@dataclass
class ACIDeviceState:
    # Core Identity (Advertisement Only)
    id: str
    name: str
    model: str

    # Operational Data (Advertisement & Characteristic)
    temperature: float
    fan_speed_on: int
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

    @property
    def is_on(self) -> bool:
        if self.fan_speed_on == 0:
            return False
        return self.mode != DeviceMode.OFF

    @classmethod
    def from_advertisement(cls, ad: ParsedAdvertisement) -> "ACIDeviceState":
        return cls(
            id=ad.id,
            name=ad.name,
            model=ad.model,
            temperature=ad.temperature,
            fan_speed_on=ad.fan_speed,
        )

    def update_from_advertisement(self, ad: ParsedAdvertisement) -> None:
        self.id = ad.id
        self.name = ad.name
        self.model = ad.model
        self.fan_speed_on = ad.fan_speed
        self.temperature = ad.temperature

    def update_from_characteristic(self, char: ParsedStatus) -> None:
        self.temperature = char.temperature
        self.fan_speed_on = char.fan_speed
        self.ramp_status = char.ramp_status
        self.mode = char.mode

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'model': self.model,
            'temperature': self.temperature,
            'fan_speed': self.fan_speed_on,
            'ramp_status': self.ramp_status.value if self.ramp_status else None,
            'mode': self.mode.value if self.mode else None,
        }
