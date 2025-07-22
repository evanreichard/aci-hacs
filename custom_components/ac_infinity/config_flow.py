import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_SERVICE_DATA

from .consts import DOMAIN, MANUFACTURER_ID
from .models import DeviceNotSupported
from .protocol import Protocol
from .state import ACIDeviceState


_LOGGER = logging.getLogger(__name__)


class ACIConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        # Ensure Unique ID & Set Address
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address

        # Validate & Parse Advertisement Data
        data = discovery_info.advertisement.manufacturer_data.get(MANUFACTURER_ID)
        if data is None:
            _LOGGER.debug("No manufacturer data for %s", self._address)
            return self.async_abort(reason="invalid_manufacturer")
        try:
            device_state = parse_advertisement_data(data)
        except DeviceNotSupported as e:
            _LOGGER.debug("Device not supported for %s: %s", self._address, e)
            return self.async_abort(reason="not_supported")
        except Exception as e:
            _LOGGER.debug("Parse failed for %s: %s", self._address, e)
            return self.async_abort(reason="invalid_data")

        # Set Title Placeholders
        self.context["title_placeholders"] = {"name": device_state.name}
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": device_state.name},
        )

    async def async_step_confirm(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="confirm")
        if self._address is None:
            return self.async_abort(reason="invalid_data")
        self._abort_if_unique_id_configured()

        # Get Service Info
        service_info = bluetooth.async_last_service_info(
            self.hass, self._address.upper(), connectable=True)
        if service_info is None:
            return self.async_show_form(step_id="confirm", errors={"base": "not_found"})

        # Validate & Parse Service Data
        data = service_info.advertisement.manufacturer_data.get(MANUFACTURER_ID)
        if data is None:
            return self.async_show_form(step_id="confirm", errors={"base": "invalid_manufacturer"})
        try:
            device_state = parse_advertisement_data(data)
        except DeviceNotSupported as e:
            _LOGGER.debug("Device not supported for %s: %s", self._address, e)
            return self.async_show_form(step_id="confirm", errors={"base": "not_supported"})
        except Exception as e:
            _LOGGER.debug("Parse failed for %s: %s", self._address, e)
            return self.async_show_form(step_id="confirm", errors={"base": "invalid_data"})

        return self.async_create_entry(
            title=f"{device_state.id} ({service_info.address})",
            data={
                CONF_ADDRESS: service_info.address,
                CONF_SERVICE_DATA: device_state,
            }
        )


def parse_advertisement_data(data: bytes) -> ACIDeviceState:
    protocol = Protocol()
    ad = protocol.parse_advertisement(data)
    return ACIDeviceState.from_advertisement(ad)
