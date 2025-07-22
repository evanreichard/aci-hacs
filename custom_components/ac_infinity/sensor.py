from typing import Any

from homeassistant.components.bluetooth.passive_update_coordinator import PassiveBluetoothCoordinatorEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from propcache import cached_property

from .consts import DOMAIN
from .device import ACIDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device: ACIDevice = hass.data[DOMAIN][entry.entry_id]
    entities = [TemperatureSensor(device)]
    async_add_entities(entities)


class ACISensor(PassiveBluetoothCoordinatorEntity[ACIDevice], SensorEntity):
    """Representation of AC Infinity sensor."""

    def __init__(
        self,
        device: ACIDevice,
    ) -> None:
        """Initialize an AC Infinity sensor."""
        super().__init__(device)
        self._attr_device_info = DeviceInfo(
            name=device.name,
            model=device.state.model,
            manufacturer="AC Infinity",
            # sw_version=device.state.version, # TODO
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
        )
        self._async_update_attrs()

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        raise NotImplementedError("Not yet implemented.")

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()


class TemperatureSensor(ACISensor):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @cached_property
    def name(self) -> str:
        return f"{self.coordinator.state.id} Temperature"

    @cached_property
    def unique_id(self) -> str:
        return f"{self.coordinator.state.id}_temperature"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self.coordinator.state.temperature
