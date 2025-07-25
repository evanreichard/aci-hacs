import math

from typing import Any
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage
from homeassistant.util.scaling import int_states_in_range

from .consts import DOMAIN
from .coordinator import ACICoordinator
from .entity import ACIEntity
from .models import DeviceMode

SPEED_RANGE = (1, 10)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ACIFan(device)])


class ACIFan(ACIEntity, FanEntity):
    _attr_speed_count = int_states_in_range(SPEED_RANGE)
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED |
        FanEntityFeature.PRESET_MODE |
        FanEntityFeature.TURN_ON |
        FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Fan"
        self._attr_unique_id = f"{self.coordinator.state.id}_fan"

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    async def async_set_percentage(self, percentage: int) -> None:
        speed = 0
        if percentage > 0:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.coordinator.bt.set_on_speed(speed)

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        speed = None
        if percentage is not None:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        await self.coordinator.bt.turn_on(speed)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.bt.turn_off()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.bt.set_mode(DeviceMode.from_string(preset_mode))

    @callback
    def _async_update_attrs(self) -> None:
        state = self.coordinator.state
        self._attr_is_on = state.mode != DeviceMode.OFF

        if state.fan_speed:
            self._attr_percentage = ranged_value_to_percentage(SPEED_RANGE, state.fan_speed)

        valid_modes = [mode for mode in DeviceMode if mode not in [DeviceMode.OFF, DeviceMode.ON]]
        self._attr_preset_modes = [mode.id_string for mode in valid_modes]
        self._attr_preset_mode = str(state.mode) if state.mode in valid_modes else None
