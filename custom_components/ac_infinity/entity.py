from typing import Any

from homeassistant.components.bluetooth.passive_update_coordinator import PassiveBluetoothCoordinatorEntity
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo

from .coordinator import ACICoordinator


class ACIEntity(PassiveBluetoothCoordinatorEntity[ACICoordinator]):
    def __init__(self, coordinator: ACICoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            name=coordinator.name,
            model=coordinator.state.model,
            manufacturer="AC Infinity",
            connections={(dr.CONNECTION_BLUETOOTH, coordinator.address)},
            # sw_version=device.state.version,
        )
        self._async_update_attrs()

    @callback
    def _async_update_attrs(self) -> None:
        raise NotImplementedError("Not yet implemented.")

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        self._async_update_attrs()
        self.async_write_ha_state()
