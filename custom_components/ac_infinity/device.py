import logging

from bleak.backends.device import BLEDevice
from logging import Logger
from typing import Callable

from .client import Client
from .models import DeviceMode
from .protocol import Command, Protocol
from .state import ACIDeviceState, AutoState


class ACIBluetoothDevice:
    def __init__(
            self,
            device: BLEDevice,
            state: ACIDeviceState,
            logger: Logger | None,
            on_state_change: Callable[[], None],
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.protocol = Protocol(self.logger)
        self.client = Client(device, self._update_from_status_data, self.logger)
        self.state = state
        self._on_state_change = on_state_change

    async def set_mode(self, mode: DeviceMode):
        await self._send_command_and_update(self.protocol.set_mode(mode))

    async def set_on_speed(self, speed: int):
        await self._send_command_and_update(self.protocol.set_on_speed(speed))

    async def set_off_speed(self, speed: int):
        await self._send_command_and_update(self.protocol.set_off_speed(speed))

    async def turn_on(self, speed: int | None):
        cmd = self.protocol.set_mode(DeviceMode.ON)
        if speed is not None:
            cmd.add(self.protocol.set_on_speed(speed))
        await self._send_command_and_update(cmd)

    async def turn_off(self):
        await self.set_mode(DeviceMode.OFF)

    async def set_auto_high_temp(self, temp: int):
        auto_state = self.state.get_auto_state()
        if auto_state is None:
            return
        auto_state.high_temp = temp
        await self._send_command_and_update(self.protocol.set_auto(auto_state))

    async def set_auto_low_temp(self, temp: int):
        auto_state = self.state.get_auto_state()
        if auto_state is None:
            return
        auto_state.low_temp = temp
        await self._send_command_and_update(self.protocol.set_auto(auto_state))

    async def set_auto_low_switch(self, on: bool):
        auto_state = self.state.get_auto_state()
        if auto_state is None:
            return
        auto_state.low_temp_on = on
        await self._send_command_and_update(self.protocol.set_auto(auto_state))

    async def set_auto_high_switch(self, on: bool):
        auto_state = self.state.get_auto_state()
        if auto_state is None:
            return
        auto_state.high_temp_on = on
        await self._send_command_and_update(self.protocol.set_auto(auto_state))

    async def _get_auto_state(self) -> AutoState | None:
        if auto_state := self.state.get_auto_state():
            return auto_state
        else:
            await self.update_model_data()
        if auto_state := self.state.get_auto_state():
            return auto_state

    async def update_model_data(self):
        await self._send_command(self.protocol.get_model_data())

    async def _send_command_and_update(self, cmd: Command):
        await self._send_command(cmd)
        await self.update_model_data()

    async def _send_command(self, cmd: Command):
        if resp := await self.client.send(cmd):
            if cmd.handle_response(resp, self.state):
                self._on_state_change()

    def _update_from_status_data(self, data: bytes) -> None:
        if self.protocol.process_status(data, self.state):
            self._on_state_change()

    def _update_from_advertisement_data(self, data: bytes) -> None:
        if self.protocol.process_advertisement(data, self.state):
            self._on_state_change()
