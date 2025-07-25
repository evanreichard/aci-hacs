from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache import cached_property

from .consts import DOMAIN
from .coordinator import ACICoordinator
from .entity import ACIEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TemperatureSensor(coordinator)])


class TemperatureSensor(ACIEntity, SensorEntity):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = f"{self.coordinator.state.id} Temperature"
        self._attr_unique_id = f"{self.coordinator.state.id}_temperature"

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self.coordinator.state.temperature
