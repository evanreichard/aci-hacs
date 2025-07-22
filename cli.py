import asyncio

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakScanner

from custom_components.ac_infinity.device import ACIBluetoothDevice
from custom_components.ac_infinity.models import DeviceMode
from custom_components.ac_infinity.protocol import CMD_TYPE_READ, CMD_TYPE_WRITE, Command, Protocol
from custom_components.ac_infinity.state import ACIDeviceState

device: ACIBluetoothDevice | None = None


def parse_advertisement_data(data: bytes) -> ACIDeviceState:
    protocol = Protocol()
    ad = protocol.parse_advertisement(data)
    return ACIDeviceState.from_advertisement(ad)


async def advertisement_callback(ble_device: BLEDevice, advertisement: AdvertisementData):
    global device

    data = advertisement.manufacturer_data.get(2306)
    if not data:
        return

    if device is not None:
        return

    state = parse_advertisement_data(data)
    device = ACIBluetoothDevice(ble_device, state, lambda: None)
    await device.client._ensure_connected()


def print_data(data: bytes):
    hex_data = data.hex()
    hex_spaced = ' '.join(hex_data[i:i+2]for i in range(0, len(hex_data), 2))
    print("\tIDX: 0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50")
    print(f"\tHEX: {hex_spaced}\n")


async def handle_command(command: str):
    global seq
    if device is None:
        return

    parts: list[str] = command.split(" ")
    sub_command: str | None = None
    if len(parts) > 1:
        command = parts[0]
        sub_command = " ".join(parts[1:])

    if command == "info":
        cmd = device.protocol.get_model_data()
        await device._send_command(cmd)
    elif command == "on":
        await device.turn_on(None)
    elif command == "off":
        await device.turn_off()
    elif command == "speed":
        if sub_command is not None:
            await device.set_speed(int(sub_command))
    elif command == "mode":
        if sub_command is not None:
            await device.set_mode(DeviceMode(int(sub_command)))
    elif command in ["write", "read"]:
        cmd_type = CMD_TYPE_WRITE if command == "write" else CMD_TYPE_READ
        if sub_command is not None:
            raw_cmd = [int(i.strip()) for i in sub_command.split(",")]
            cmd = Command(cmd_type, raw_cmd, raw_resp)
            await device._send_command(cmd)

    print(device.state)


def raw_resp(data: bytes, _) -> bool:
    print_data(data)
    return False


async def run_scanner():
    scanner = BleakScanner(advertisement_callback)
    await scanner.start()

    try:
        while True:
            command = await asyncio.to_thread(input)
            await handle_command(command)
    except KeyboardInterrupt:
        await scanner.stop()

asyncio.run(run_scanner())
