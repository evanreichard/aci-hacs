import logging

from bleak.backends.device import BLEDevice
from logging import Logger
from typing import Callable

from .client import Client
from .models import DeviceMode
from .protocol import Command, Protocol
from .state import ACIDeviceState


class ACIBluetoothDevice:
    def __init__(
            self,
            device: BLEDevice,
            state: ACIDeviceState,
            update_callback: Callable[[], None],
            logger: Logger | None,
    ):
        self.state = state
        self.protocol = Protocol(logger)
        self.client = Client(device, on_status_update=self._update_from_status_data, logger=logger)
        self.logger = logger or logging.getLogger(__name__)

        self._address = device.address
        self._update_callback = update_callback

    async def set_mode(self, mode: DeviceMode):
        await self._send_command(self.protocol.set_mode(mode))

    async def set_on_speed(self, speed: int):
        await self._send_command(self.protocol.set_on_speed(speed))

    async def set_off_speed(self, speed: int):
        await self._send_command(self.protocol.set_off_speed(speed))

    async def turn_on(self, speed: int | None):
        cmd = self.protocol.set_mode(DeviceMode.ON)
        if speed is not None:
            cmd.add(self.protocol.set_on_speed(speed))
        await self._send_command(cmd)

    async def turn_off(self):
        await self.set_mode(DeviceMode.OFF)

    async def _send_command(self, cmd: Command):
        if resp := await self.client.send(cmd):
            if cmd.handle_response(resp, self.state):
                self._update_callback()

    async def _do_poll(self, _) -> None:
        try:
            await self._send_command(self.protocol.get_model_data())
        except Exception as e:
            self.logger.error("failed to poll model data [%s]: %s", self._address, e)

    def _update_from_status_data(self, data: bytes) -> None:
        if self.protocol.process_status(data, self.state):
            self._update_callback()

    def _update_from_advertisement_data(self, data: bytes) -> None:
        if self.protocol.process_advertisement(data, self.state):
            self._update_callback()
