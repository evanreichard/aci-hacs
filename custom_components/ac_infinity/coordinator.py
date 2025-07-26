from logging import Logger
from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import ActiveBluetoothDataUpdateCoordinator
from homeassistant.core import CoreState, HomeAssistant, callback

from .consts import MANUFACTURER_ID
from .device import ACIBluetoothDevice
from .state import ACIDeviceState


class ACICoordinator(ActiveBluetoothDataUpdateCoordinator[None]):
    bt: ACIBluetoothDevice
    state: ACIDeviceState

    def __init__(
        self,
        hass: HomeAssistant,
        device: BLEDevice,
        state: ACIDeviceState,
        logger: Logger,
    ) -> None:
        self.state = state
        self.bt = ACIBluetoothDevice(
            device=device,
            state=state,
            on_state_change=self.async_update_listeners,
            logger=logger,
        )

        super().__init__(
            hass=hass,
            logger=logger,
            address=device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._do_poll,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )

    async def _do_poll(self, _) -> None:
        try:
            await self.bt.update_model_data()
        except Exception as e:
            self.logger.error("failed to update model data: %s", e)

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        return (
            self.hass.state == CoreState.running
            and (seconds_since_last_poll is None or seconds_since_last_poll > 30)
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True)
            )
        )

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        data = service_info.advertisement.manufacturer_data.get(MANUFACTURER_ID)
        if data is None:
            self.logger.warning("no manufacturer data for %s", self.address)
        else:
            self.bt._update_from_advertisement_data(data)
        super()._async_handle_bluetooth_event(service_info, change)
