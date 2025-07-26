from dataclasses import dataclass, field
from logging import Logger
import logging
from typing import Callable

from .state import ACIDeviceState, AutoState
from .models import DeviceMode, DeviceType, RampStatus


PACKET_HEAD = bytes([165, 0])
CMD_TYPE_READ = 1
CMD_TYPE_WRITE = 3


@dataclass
class Command:
    type: int
    command: list[int]
    _callbacks: list[
        Callable[[bytes, ACIDeviceState], bool]
    ] = field(default_factory=list, init=False)

    def compile(self, seq: int) -> bytes:
        return build_command(bytes(self.command), self.type, seq)

    def add(self, cmd: "Command"):
        self.command.extend(cmd.command)
        self._callbacks.extend(cmd._callbacks)

    def with_callback(self, callback: Callable[[bytes, ACIDeviceState], bool]) -> "Command":
        self._callbacks.append(callback)
        return self

    def has_callbacks(self) -> bool:
        return len(self._callbacks) > 0

    def handle_response(self, data: bytes, state: ACIDeviceState) -> bool:
        did_update = False
        for cb in self._callbacks:
            did_update |= cb(data, state)
        return did_update


class Protocol:
    def __init__(self, logger: Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def set_mode(self, mode: DeviceMode) -> Command:
        return Command(CMD_TYPE_WRITE, [16, 1, mode.value])

    def set_on_speed(self, speed: int) -> Command:
        return Command(CMD_TYPE_WRITE, [18, 1, speed])

    def set_off_speed(self, speed: int) -> Command:
        return Command(CMD_TYPE_WRITE, [17, 1, speed])

    def set_auto(self, state: AutoState) -> Command:
        auto_on_state = (state.low_temp_on << 2) | (state.high_temp_on << 3)
        return Command(CMD_TYPE_WRITE, [19, 7, auto_on_state, state.high_temp, state.high_temp, state.low_temp, state.low_temp])

    def get_model_data(self):
        return Command(CMD_TYPE_READ, [16, 17, 18, 19, 20, 21, 22, 23]).with_callback(self.process_model_data)

    def process_model_data(self, data: bytes, state: ACIDeviceState) -> bool:
        """
        IDX: 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53
        HEX: A5 13 00 2A 00 03 37 D5 00 01 10 01 01 11 01 02 12 01 08 13 07 00 09 74 86 0C 79 8C 14 04 00 00 01 2C 15 04 00 00 01 2C 16 08 00 00 01 2C 00 00 01 2C 17 00 C7 6D
                                                  │       ├┘       ├┘       ├┘    ├┘    ├┘                   └─┬─┘             └─┬─┘             └─┬─┘       └─┬─┘
                ┌─────────────────────────────────┤  ┌────┴────┐   │ ┌──────┴──┐  │ ┌───┴────┐           ┌─────┴─────┐     ┌─────┴──────┐     ┌────┴───┐  ┌────┴────┐
                │            Device Mode          │  │Speed Off│   │ │ Auto On │  │ │Auto Low│           │Timer to On│     │Timer to Off│     │Cycle On│  │Cycle Off│
                │1 = off; 2 = on; 3 = auto temp   │  └─────────┘   │ │H (Bit 3)│  │ └────────┘           └───────────┘     └────────────┘     └────────┘  └─────────┘
                │4 = timer to on; 5 = timer to off│   ┌────────┬───┘ │L (Bit 2)│  ├─────────┐
                │        6 = cycle on or off      │   │Speed On│     └─────────┘  │Auto High│
                └─────────────────────────────────┘   └────────┘                  └─────────┘
        """
        if len(data) != 54:
            self.logger.warning("invalid data length for model data: %s", len(data))
            return False

        # Device Mode (Byte 12)
        try:
            state.mode = DeviceMode(data[12])
        except:
            pass

        # Update State
        state.auto_high_temp = data[23]
        state.auto_high_temp_on = bool(data[21] & (1 << 3))
        state.auto_low_temp = data[25]
        state.auto_low_temp_on = bool(data[21] & (1 << 2))
        state.cycle_off_time = int.from_bytes(data[48:50])
        state.cycle_on_time = int.from_bytes(data[44:46])
        state.fan_speed_off = data[15]
        state.fan_speed_on = data[18]

        self.logger.debug("updated state via model info")
        return True

    def process_advertisement(self, data: bytes, state: ACIDeviceState) -> bool:
        """
        IDX: 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26
        HEX: A4 C1 38 5F 42 9B 53 34 30 42 4D 03 06 00 05 CD 00 00 04 00 00 00 00 00 00 00 00
                               └───┬───────────┘ ├┘    ├───┘        │
                 ┌─────────────────┤ ┌───────────┤ ┌───┴──────────┐ ├─────────┐
                 │Device Identifier│ │Device Type│ │     Temp     │ │Fan Speed│
                 │     (ASCII)     │ └───────────┘ │05CD = 14.85°C│ │ (0 - A) │
                 └─────────────────┘               └──────────────┘ └─────────┘
        """
        if len(data) != 27:
            self.logger.warning("invalid data length for advertisement data: %s", len(data))
            return False

        # Device Type (Byte 12)
        try:
            device = DeviceType(data[12])
        except ValueError:
            self.logger.warning("device not supported: %d", data[12])
            return False

        device_id = "{}-{}".format(device.prefix, data[6:11].decode('ascii'))
        device_name = "{} ({})".format(device, device_id)

        # Temperature (Bytes 14-15, Big Endian)
        temp_raw = int.from_bytes(data[14:16], 'big')
        temperature = temp_raw / 100.0  # 05CD = 1485 = 14.85°C

        # Fan Speed (Byte 18 Lower Nibble)
        fan_speed = data[18] & 0x0F

        # Update State
        state.id = device_id
        state.name = device_name
        state.model = device.model
        state.fan_speed = fan_speed
        state.temperature = temperature

        self.logger.debug("updated state via advertisement")
        return True

    def process_status(self, data: bytes, state: ACIDeviceState) -> bool:
        """
        IDX: 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17
        HEX: 1E FF 02 09 03 0C 00 00 07 E4 00 00 00 00 27 10 00 32
               ┌──────────────┬──────┴───┘                   │  ││
               │     Temp     │ ┌────────────────────────────┘  ││
               │07E4 = 20.20°C│ │ ┌─────────┬───────────────────┘│
               └──────────────┘ │ │Fan Speed│ ┌──────────────────┴──────────────┐
             ┌──────────────────┤ │ (0 - A) │ │            Device Mode          │
             │Fan Ramping Status│ └─────────┘ │1 = off; 2 = on; 3 = auto temp   │
             │(8 = up, 4 = down)│             │4 = timer to on; 5 = timer to off│
             └──────────────────┘             │        6 = cycle on or off      │
                                              └─────────────────────────────────┘
        """
        if len(data) != 18:
            self.logger.warning("invalid data length for status data: %s", len(data))
            return False

        # Temperature (Bytes 8-9, Big Endian)
        temp_raw = int.from_bytes(data[8:10], 'big')
        state.temperature = temp_raw / 100.0  # 07E4 = 2020 = 20.20°C

        # Fan Speed (Byte 14 Upper Nibble)
        state.fan_speed = data[17] >> 4

        # Ramp Status (Byte 16 Upper Nibble)
        try:
            state.ramp_status = RampStatus(data[16] >> 4)
        except ValueError:
            state.ramp_status = RampStatus.NONE

        # Device Mode (Byte 17 Lower Nibble)
        try:
            state.mode = DeviceMode(data[17] & 0x0F)
        except ValueError:
            state.mode = DeviceMode.OFF

        self.logger.debug("updated state via status")
        return True


def build_command(payload: bytes, command_type: int, seq: int):
    d = bytearray(len(payload) + 12)
    d[:len(PACKET_HEAD)] = PACKET_HEAD
    add_int16(d, 2, len(payload))
    add_int16(d, 4, seq)
    add_int16(d, 6, crc16(d, 0, 6))
    d[8] = 0
    d[9] = command_type
    d[10:10+len(payload)] = payload
    add_int16(d, len(payload) + 10, crc16(d, 8, len(payload) + 2))
    seq += 1
    return bytes(d)


def crc16(d, i, n):
    b = 0xffff
    for k in range(i, i + n):
        b2 = (((b << 8) | (b >> 8)) & 0xffff) ^ (d[k] & 0xff)
        b3 = b2 ^ ((b2 & 0xff) >> 4)
        b4 = b3 ^ ((b3 << 12) & 0xffff)
        b = b4 ^ (((b4 & 0xff) << 5) & 0xffff)
    return b


def add_int16(d, i, j):
    d[i] = (j >> 8) & 0xff
    d[i+1] = j & 0xff
