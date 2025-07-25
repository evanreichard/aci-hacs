import asyncio
import logging

from typing import Callable
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from bleak.backends.device import BLEDevice

from .protocol import Command

DISCONNECT_TIMEOUT = 30
RESPONSE_TIMEOUT = 5

WRITE_CHAR = "70d51001-2c7f-4e75-ae8a-d758951ce4e0"
READ_NOTIFY_CHAR = "70d51002-2c7f-4e75-ae8a-d758951ce4e0"

WRITE_RESPONSE_HEADER = bytes([0xA5, 0x13, 0x00])  # LEN: 14
NOTIFY_STATUS_HEADER = bytes([0x1E, 0xFF, 0x02])  # LEN: 18


class Client:
    def __init__(
            self,
            ble_device: BLEDevice,
            on_status_update: Callable[[bytes], None],
            logger: logging.Logger | None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self._ble_device = ble_device
        self._client = BleakClientWithServiceCache(ble_device)
        self._seq = 0

        self._on_status_update = on_status_update
        self._loop = asyncio.get_running_loop()
        self._connect_lock: asyncio.Lock = asyncio.Lock()
        self._seq_lock: asyncio.Lock = asyncio.Lock()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._response_futures: dict[int, asyncio.Future[bytes]] = {}

    async def send(self, command: Command) -> bytes | None:
        # Ensure Connection & Update Sequence
        try:
            await self._ensure_connected()
        except Exception as e:
            self.logger.error("failed to to send command: %s", e)
            return

        # Increment Sequence
        async with self._seq_lock:
            seq = self._seq
            self._seq += 1

        # Command - No Callback
        if not command.has_callbacks():
            await self._client.write_gatt_char(WRITE_CHAR, command.compile(seq), True)
            self.logger.debug("sent command without callback(s) for seq-%d", seq)
            return

        # Create Future
        future = asyncio.Future[bytes]()
        self._response_futures[seq] = future

        # Send & Wait
        await self._client.write_gatt_char(WRITE_CHAR, command.compile(seq), True)
        self.logger.debug("sent command with callback(s) for seq-%d", seq)
        try:
            resp = await asyncio.wait_for(future, timeout=RESPONSE_TIMEOUT)
            self.logger.debug("received command response for seq-%d: length: %d", seq, len(resp))
            return resp
        except Exception:
            self.logger.error("failed to receive command response for seq-%d", seq)
        finally:
            self._response_futures.pop(seq, None)

    async def _ensure_connected(self):
        async with self._connect_lock:
            if self._client and self._client.is_connected:
                self._reset_disconnect_timer()
                self.logger.debug("already connected")
                return

            self.logger.debug("connecting")
            try:
                self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    self._ble_device,
                    self._ble_device.address,
                    use_services_cache=True,
                    ble_device_callback=lambda: self._ble_device,
                )
                if not self._client.is_connected:
                    raise
            except Exception as e:
                self.logger.error("failed to connect: %s", e)
                raise
            self.logger.debug("successfully connected")

            self._reset_disconnect_timer()
            await self._client.start_notify(READ_NOTIFY_CHAR, self._notification_handler)
            self.logger.debug("started notify")
            await asyncio.sleep(2)

    def _notification_handler(self, _, data: bytearray):
        header = data[:3]
        if header == NOTIFY_STATUS_HEADER:
            return self._on_status_update(bytes(data))
        elif header == WRITE_RESPONSE_HEADER:
            seq = data[5]
            if seq in self._response_futures:
                self.logger.debug("received write response for seq-%d", seq)
                self._response_futures[seq].set_result(bytes(data))
            else:
                self.logger.debug("received write response for unknown seq-%d", seq)
        else:
            self.logger.warning("received unknown data: %s", format_as_hex(bytes(data)))

    def _reset_disconnect_timer(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._disconnect_timer = self._loop.call_later(DISCONNECT_TIMEOUT, self._disconnect)

    def _disconnect(self) -> None:
        asyncio.create_task(self._execute_disconnect())

    async def _execute_disconnect(self) -> None:
        self.logger.debug("disconnecting")
        async with self._connect_lock:
            if not self._client.is_connected:
                return
            await self._client.stop_notify(READ_NOTIFY_CHAR)
            await self._client.disconnect()


def format_as_hex(data: bytes) -> str:
    hex_data = data.hex().upper()
    return ' '.join(hex_data[i:i+2]for i in range(0, len(hex_data), 2))
