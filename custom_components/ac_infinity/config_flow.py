import logging

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_SERVICE_DATA

from .consts import DOMAIN, MANUFACTURER_ID
from .protocol import Protocol
from .state import ACIDeviceState


logger = logging.getLogger(__name__)


class ACIConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._state: ACIDeviceState = ACIDeviceState()

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        # Ensure Unique ID & Set Address
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address

        # Validate & Parse Advertisement Data
        data = discovery_info.advertisement.manufacturer_data.get(MANUFACTURER_ID)
        if data is None:
            logger.debug("No manufacturer data for %s", self._address)
            return self.async_abort(reason="invalid_manufacturer")

        # Parse Advertisement Data
        proto = Protocol()
        if not proto.process_advertisement(data, self._state):
            logger.debug("device not supported for %s", self._address)
            return self.async_abort(reason="not_supported")

        # Validate Data
        if self._state.name is None or self._state.id is None:
            return self.async_abort(reason="invalid_data")

        # Set Title Placeholders
        self.context["title_placeholders"] = {"name": self._state.name}
        return self.async_show_form(step_id="confirm")

    async def async_step_confirm(self, user_input=None):
        # Validate Input & Data
        if user_input is None:
            return self.async_show_form(step_id="confirm")
        if self._address is None:
            return self.async_abort(reason="invalid_data")
        self._abort_if_unique_id_configured()

        # Create Entry
        return self.async_create_entry(
            title=f"{self._state.id} ({self._address})",
            data={
                CONF_ADDRESS: self._address,
                CONF_SERVICE_DATA: self._state,
            }
        )
