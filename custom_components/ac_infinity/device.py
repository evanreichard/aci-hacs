import logging
from typing import Callable

from bleak.backends.device import BLEDevice
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import ActiveBluetoothDataUpdateCoordinator
from homeassistant.core import CoreState, HomeAssistant, callback

from .client import Client
from .consts import MANUFACTURER_ID
from .models import DeviceMode, DeviceNotSupported
from .protocol import Command, Protocol
from .state import ACIDeviceState


_LOGGER = logging.getLogger(__name__)


class ACIBluetoothDevice:
    def __init__(
            self,
            device: BLEDevice,
            state: ACIDeviceState,
            update_callback: Callable[[], None],
    ):
        self.state = state
        self.protocol = Protocol()
        self.client = Client(device, on_status_update=self._update_from_status_data)

        self._address = device.address
        self._update_callback = update_callback

    async def set_mode(self, mode: DeviceMode):
        await self._send_command(self.protocol.set_mode(mode))

    async def turn_on(self, speed: int | None):
        await self.set_mode(DeviceMode.ON)
        if speed is not None:
            await self.set_speed(speed)

    async def turn_off(self):
        await self.set_mode(DeviceMode.OFF)

    async def set_speed(self, speed: int):
        await self._send_command(self.protocol.set_speed(speed))

    async def _send_command(self, cmd: Command):
        if resp := await self.client.send(cmd):
            if cmd.handle_response(resp, self.state):
                self._update_callback()

    async def _do_poll(self, _) -> None:
        try:
            await self._send_command(self.protocol.get_model_data())
        except Exception as e:
            _LOGGER.error("failed to poll model data [%s]: %s", self._address, e)

    def _update_from_status_data(self, data: bytes) -> None:
        try:
            parsed_data = self.protocol.parse_status(data)
            self.state.update_from_characteristic(parsed_data)
            self._update_callback()
        except Exception as e:
            _LOGGER.error("failed to update from status data [%s]: %s", self._address, e)

    def _update_from_advertisement_data(self, data: bytes) -> None:
        try:
            parsed_data = self.protocol.parse_advertisement(data)
            self.state.update_from_advertisement(parsed_data)
            self._update_callback()
        except DeviceNotSupported as e:
            _LOGGER.warning("Device not supported for [%s]: %s", self._address, e)
        except Exception as e:
            _LOGGER.error("failed to update from status data [%s]: %s", self._address, e)


class ACIDevice(ActiveBluetoothDataUpdateCoordinator[None]):
    bt: ACIBluetoothDevice
    state: ACIDeviceState

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        device: BLEDevice,
        state: ACIDeviceState,
    ) -> None:
        self.bt = ACIBluetoothDevice(device, state, self.async_update_listeners)
        self.state = state

        super().__init__(
            hass=hass,
            logger=logger,
            address=device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self.bt._do_poll,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )

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
            _LOGGER.warning("No manufacturer data for %s", self.address)
        else:
            self.bt._update_from_advertisement_data(data)
        super()._async_handle_bluetooth_event(service_info, change)
