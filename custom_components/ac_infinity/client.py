import time
import logging
import asyncio

from typing import Callable
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from bleak.backends.device import BLEDevice

from .protocol import Command, print_data

DISCONNECT_TIMEOUT = 30
RESPONSE_TIMEOUT = 5

WRITE_CHAR = "70d51001-2c7f-4e75-ae8a-d758951ce4e0"
READ_NOTIFY_CHAR = "70d51002-2c7f-4e75-ae8a-d758951ce4e0"

WRITE_RESPONSE_HEADER = bytes([0xA5, 0x13, 0x00])  # LEN: 14
NOTIFY_STATUS_HEADER = bytes([0x1E, 0xFF, 0x02])  # LEN: 18


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class Client:
    def __init__(self, ble_device: BLEDevice, on_status_update: Callable[[bytes], None]):
        self._ble_device = ble_device
        self._client = BleakClientWithServiceCache(ble_device)
        self._seq = 0

        self._on_status_update = on_status_update
        self._loop = asyncio.get_running_loop()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._response_futures: dict[int, asyncio.Future[bytes]] = {}

    async def send(self, command: Command) -> bytes | None:
        # Ensure Connection & Update Sequence
        try:
            await self._ensure_connected()
        except Exception as e:
            return

        seq = self._seq
        self._seq += 1

        # Create Future
        future = asyncio.Future[bytes]()
        self._response_futures[seq] = future

        # Send & Wait
        await self._client.write_gatt_char(WRITE_CHAR, command.compile(seq), True)
        _LOGGER.debug("sent command")
        try:
            resp = await asyncio.wait_for(future, timeout=RESPONSE_TIMEOUT)
            _LOGGER.debug("received command response length: %d", len(resp))
            return resp
        except Exception as e:
            _LOGGER.error("failed to receive command response: %s", type(e))
        finally:
            self._response_futures.pop(seq, None)

    async def _ensure_connected(self):
        async with self._lock:
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                _LOGGER.debug("already connected")
                return

            _LOGGER.debug("connecting")
            try:
                self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    self._ble_device,
                    self._ble_device.address,
                    use_services_cache=True,
                    ble_device_callback=lambda: self._ble_device,
                )
            except Exception as e:
                _LOGGER.error("failed to connect: %s", type(e))
                return
            _LOGGER.debug("successfully connected")

            self._reset_disconnect_timer()
            await self._client.start_notify(READ_NOTIFY_CHAR, self._notification_handler)
            await asyncio.sleep(2)
            _LOGGER.debug("started notify")

    def _notification_handler(self, char: BleakGATTCharacteristic, data: bytearray):
        header = data[:3]
        if header == NOTIFY_STATUS_HEADER:
            return self._on_status_update(bytes(data))
        elif header == WRITE_RESPONSE_HEADER:
            seq = data[5]
            if seq in self._response_futures:
                self._response_futures[seq].set_result(bytes(data))
        else:
            print("UNKNOWN DATA:")
            print_data(bytes(data))
            return

    def _reset_disconnect_timer(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._disconnect_timer = self._loop.call_later(DISCONNECT_TIMEOUT, self._disconnect)

    def _disconnect(self) -> None:
        asyncio.create_task(self._execute_disconnect())

    async def _execute_disconnect(self) -> None:
        async with self._lock:
            if not self._client.is_connected:
                return
            await self._client.stop_notify(READ_NOTIFY_CHAR)
            await self._client.disconnect()
