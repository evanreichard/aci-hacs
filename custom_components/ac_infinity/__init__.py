import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_SERVICE_DATA
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .consts import DOMAIN
from .device import ACIDeviceState
from .coordinator import ACICoordinator


PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.FAN, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Get Device Configuration
    address: str = entry.data[CONF_ADDRESS]
    raw_data = entry.data[CONF_SERVICE_DATA]
    if isinstance(raw_data, dict):
        state = ACIDeviceState(**raw_data)
    else:
        state = raw_data

    # Get BLEDevice
    ble_device = bluetooth.async_ble_device_from_address(hass, address.upper(), True)
    if not ble_device:
        raise ConfigEntryNotReady(f"Could not get AC Infinity device with address {address}")

    # Setup Coordinator
    device_logger = logging.getLogger(f"{DOMAIN}.{entry.entry_id}")
    coordinator = ACICoordinator(hass, ble_device, state, device_logger)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entry.async_on_unload(coordinator.async_start())
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    if entry.title != f"{coordinator.state.id} ({coordinator.address})":
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
