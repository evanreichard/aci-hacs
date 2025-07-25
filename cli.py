import asyncio
import datetime
import json
import logging

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakScanner
from collections.abc import Callable
from datetime import datetime
from logging import Handler
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, Input

from custom_components.ac_infinity.client import format_as_hex
from custom_components.ac_infinity.device import ACIBluetoothDevice
from custom_components.ac_infinity.models import DeviceMode
from custom_components.ac_infinity.protocol import CMD_TYPE_READ, CMD_TYPE_WRITE, Command
from custom_components.ac_infinity.state import ACIDeviceState


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)


class CLI:
    def __init__(self, log_handler: Handler, update_callback: Callable[[], None]):
        self.device: ACIBluetoothDevice | None = None
        self.state = ACIDeviceState()
        self.scanner = BleakScanner(self.advertisement_callback)
        self.seq = 0

        self._log_handler = log_handler
        self._update_callback = update_callback

    async def advertisement_callback(self, ble_device: BLEDevice, advertisement: AdvertisementData):
        # Get Manufacturer Data
        data = advertisement.manufacturer_data.get(2306)
        if not data:
            return

        # Update State
        if self.device is not None:
            if self.device.protocol.process_advertisement(data, self.state):
                self._update_callback()
            return

        # Create Logger
        logger = logging.getLogger(f"ac_infinity.{ble_device.address}")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self._log_handler)
        logger.propagate = False

        # Create Device & Initialize
        self.device = ACIBluetoothDevice(
            device=ble_device,
            state=self.state,
            logger=logger,
            update_callback=self._update_callback,
        )

        # Update State
        if self.device.protocol.process_advertisement(data, self.state):
            self._update_callback()
        await self.device.client._ensure_connected()

    async def handle_command(self, command: str, cb: Callable[[str], None]):
        if self.device is None:
            cb("ERROR: DEVICE NOT CONNECTED")
            return

        # Parse Command & SubCommand
        parts: list[str] = command.split(" ")
        sub_command: str | None = None
        if len(parts) > 1:
            command = parts[0]
            sub_command = " ".join(parts[1:])

        def cmd_cb(data: bytes, _) -> bool:
            cb(format_as_hex(data))
            return False

        # Handle Command
        cmd: Command | None = None
        if command == "info":
            cmd = self.device.protocol.get_model_data()
        elif command == "on":
            cmd = self.device.protocol.set_mode(DeviceMode.ON)
        elif command == "off":
            cmd = self.device.protocol.set_mode(DeviceMode.OFF)
        elif command == "speed":
            if sub_command is not None:
                cmd = self.device.protocol.set_on_speed(int(sub_command))
        elif command == "mode":
            if sub_command is not None:
                cmd = self.device.protocol.set_mode(DeviceMode(int(sub_command)))
        elif command in ["write", "read"]:
            cmd_type = CMD_TYPE_WRITE if command == "write" else CMD_TYPE_READ
            if sub_command is not None:
                raw_cmd = [int(i.strip()) for i in sub_command.split(",")]
                cmd = Command(cmd_type, raw_cmd)

        if cmd is not None:
            await self.device._send_command(cmd.with_callback(cmd_cb))
        else:
            cb("ERROR: NOT A VALID COMMAND")


class CommandEntry(Static):
    def __init__(self, command: str, result: str):
        self.command = command
        self.timestamp = datetime.now().replace(microsecond=0).isoformat()
        self.result = result
        content = f"[{self.timestamp}] $ {self.command}\n\n{self.result}"
        super().__init__(content, classes="command-entry")

    def update_result(self, result: str):
        self.result = result
        content = f"[{self.timestamp}] $ {self.command}\n\n{self.result}"
        self.update(content)


class ACInfinityCLI(App):
    CSS = """
    #logs {
        width: 100%;
        height: 40%;
        border: solid white;
    }

    #state {
        width: 30%;
        height: 100%;
        border: solid white;
    }

    #command_history {
        width: 70%;
        border: solid white;
    }

    #command_input {
        width: 100%;
        height: 3;
        border: solid white;
    }

    .command-entry {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        border: solid $primary 50%;
    }
    """

    def __init__(self):
        super().__init__()

        log_handler = TextualLogHandler(self)
        self.cli = CLI(log_handler, self.on_state_update)
        self.command_history: list[CommandEntry] = []
        self.log_entries: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with ScrollableContainer(id="logs"):
                yield Static("", id="logs-content")
            with Horizontal():
                with ScrollableContainer(id="command_history"):
                    for cmd in self.command_history:
                        yield cmd
                yield Static(id="state")
            yield Input(placeholder="Enter Command", id="command_input")

    def on_mount(self):
        self.logs_container = self.query_one("#logs", ScrollableContainer)
        self.logs_content = self.query_one("#logs-content", Static)
        self.state_widget = self.query_one("#state", Static)
        self.history_container = self.query_one("#command_history", ScrollableContainer)
        self.command_widget = self.query_one("#command_input", Input)
        self.command_widget.focus()

    def on_state_update(self):
        self.state_widget.update(json.dumps(self.cli.state.to_dict(), indent=2))

    def on_log_message(self, msg: str):
        timestamp = datetime.now().replace(microsecond=0).isoformat()
        self.log_entries.append(f"[{timestamp}] {msg}")
        self.logs_content.update("\n".join(self.log_entries))
        self.logs_container.scroll_end(animate=False)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if not command:
            return

        # Set Loading Message
        cmd_entry = CommandEntry(command, "--- LOADING ---")
        self.command_history.append(cmd_entry)
        self.history_container.mount(cmd_entry)
        self.history_container.scroll_end(animate=False)

        # Define Callback
        def cmd_cb(result: str):
            cmd_entry.update_result(result)
            self.history_container.scroll_end(animate=False)
            self.command_widget.focus()

        # Send Command
        self.command_widget.value = ""
        asyncio.create_task(self.cli.handle_command(command, cmd_cb))


class TextualLogHandler(Handler):
    def __init__(self, ui_app: ACInfinityCLI):
        super().__init__()
        self.ui_app = ui_app

    def emit(self, record):
        log_message = self.format(record)
        self.ui_app.on_log_message(log_message)


async def run_cli():
    # Start BLE Scanner
    ui = ACInfinityCLI()
    await ui.cli.scanner.start()

    # Start Textual
    ui_task = asyncio.create_task(ui.run_async())
    try:
        await ui_task
    except KeyboardInterrupt:
        await ui.cli.scanner.stop()
        ui_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_cli())
