from typing import Any
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.ac_infinity.models import DeviceMode

from .consts import DOMAIN
from .coordinator import ACICoordinator
from .entity import ACIEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([Climate(coordinator)])


class Climate(ACIEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_high = 100
    _attr_target_temperature_low = 0
    _attr_target_temperature_step = 1
    _attr_supported_features = (
        ClimateEntityFeature.FAN_MODE |
        ClimateEntityFeature.TARGET_TEMPERATURE |
        ClimateEntityFeature.TARGET_TEMPERATURE_RANGE |
        ClimateEntityFeature.TURN_OFF |
        ClimateEntityFeature.TURN_ON
    )

    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.HEAT_COOL,
        HVACMode.FAN_ONLY
    ]
    _attr_fan_modes = [str(mode) for mode in DeviceMode]

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self.logger = coordinator.logger
        self._attr_name = f"Climate"
        self._attr_unique_id = f"{self.coordinator.state.id}_climate"

    async def async_turn_off(self) -> None:
        await self.coordinator.bt.turn_off()

    async def async_turn_on(self) -> None:
        await self.coordinator.bt.set_mode(DeviceMode.AUTO_TEMP)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self.coordinator.bt.set_mode(DeviceMode.from_string(fan_mode))

    async def async_set_temperature(self, **kwargs: Any) -> None:
        target_high_temp: float | None = kwargs.get("target_temp_high")
        target_low_temp: float | None = kwargs.get("target_temp_low")
        if target_high_temp is not None and target_low_temp is not None:
            await self.coordinator.bt.set_auto_temp(target_low_temp, target_high_temp)
        if target_low_temp is not None:
            await self.coordinator.bt.set_auto_low_temp(target_low_temp)
        if target_high_temp is not None:
            await self.coordinator.bt.set_auto_high_temp(target_high_temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Set Simple On / Off
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.bt.turn_off()
            return
        if hvac_mode == HVACMode.FAN_ONLY:
            await self.coordinator.bt.turn_on(None)
            return

        # Ensure Mode
        state = self.coordinator.state
        if state.mode != DeviceMode.AUTO_TEMP:
            await self.coordinator.bt.set_mode(DeviceMode.AUTO_TEMP)

        # Ensure Low / High Switches
        if hvac_mode == HVACMode.HEAT:
            if not state.auto_low_temp_on:
                await self.coordinator.bt.set_auto_low_switch(True)
            if state.auto_high_temp_on is None or state.auto_high_temp_on:
                await self.coordinator.bt.set_auto_high_switch(False)
        elif hvac_mode == HVACMode.COOL:
            if state.auto_low_temp_on is None or state.auto_low_temp_on:
                await self.coordinator.bt.set_auto_low_switch(False)
            if not state.auto_high_temp_on:
                await self.coordinator.bt.set_auto_high_switch(True)
        elif hvac_mode == HVACMode.HEAT_COOL:
            if not state.auto_low_temp_on:
                await self.coordinator.bt.set_auto_low_switch(True)
            if not state.auto_high_temp_on:
                await self.coordinator.bt.set_auto_high_switch(True)

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        # Validate Needed Attributes
        mode = self.coordinator.state.mode
        speed = self.coordinator.state.fan_speed
        temperature = self.coordinator.state.temperature
        state = self.coordinator.state.get_auto_state()
        if state is None or mode is None or temperature is None or speed is None:
            self.logger.warning("missing attributes for climate update")
            return

        # Set Base State
        self._attr_current_temperature = temperature
        self._attr_hvac_mode = HVACMode.FAN_ONLY
        self._attr_hvac_action = HVACAction.FAN
        self._attr_fan_mode = str(mode)

        # Set State
        if mode == DeviceMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF
        elif mode == DeviceMode.AUTO_TEMP:
            self._attr_hvac_action = HVACAction.IDLE
            self._attr_target_temperature_high = state.high_temp
            self._attr_target_temperature_low = state.low_temp

            if state.low_temp_on and state.high_temp_on:
                self._attr_hvac_mode = HVACMode.HEAT_COOL
            elif state.high_temp_on:
                self._attr_hvac_mode = HVACMode.COOL
            elif state.low_temp_on:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF
                return

            if speed:
                if self._attr_hvac_mode in (HVACMode.COOL, HVACMode.HEAT_COOL) and temperature > state.high_temp:
                    self._attr_hvac_action = HVACAction.COOLING
                elif self._attr_hvac_mode in (HVACMode.HEAT, HVACMode.HEAT_COOL) and temperature < state.low_temp:
                    self._attr_hvac_action = HVACAction.HEATING
