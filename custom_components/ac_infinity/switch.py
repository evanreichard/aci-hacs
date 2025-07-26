from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .consts import DOMAIN
from .coordinator import ACICoordinator
from .entity import ACIEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AutoHighTemperatureSwitch(coordinator),
        AutoLowTemperatureSwitch(coordinator),
    ])


class AutoHighTemperatureSwitch(ACIEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Auto High Temp Enabled"
        self._attr_unique_id = f"{self.coordinator.state.id}_auto_high_temp_enabled"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.bt.set_auto_high_switch(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.bt.set_auto_high_switch(False)

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_is_on = self.coordinator.state.auto_high_temp_on


class AutoLowTemperatureSwitch(ACIEntity, SwitchEntity):
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Auto Low Temp Enabled"
        self._attr_unique_id = f"{self.coordinator.state.id}_auto_low_temp_enabled"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.bt.set_auto_low_switch(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.bt.set_auto_low_switch(False)

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_is_on = self.coordinator.state.auto_low_temp_on
