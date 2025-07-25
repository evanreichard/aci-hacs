from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .consts import DOMAIN
from .coordinator import ACICoordinator
from .entity import ACIEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ACICoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AutoHighTemperature(coordinator),
        AutoLowTemperature(coordinator),
        CycleOffTime(coordinator),
        CycleOnTime(coordinator),
        OffSpeed(coordinator),
        OnSpeed(coordinator),
        TimerToOffTime(coordinator),
        TimerToOnTime(coordinator)
    ])


class AutoHighTemperature(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 50

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Auto High Temp"
        self._attr_unique_id = f"{self.coordinator.state.id}_auto_high_temp"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_auto_high_temp(int(value))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.coordinator.state.auto_high_temp


class AutoLowTemperature(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 50

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Auto Low Temp"
        self._attr_unique_id = f"{self.coordinator.state.id}_auto_low_temp"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_auto_low_temp(int(value))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.coordinator.state.auto_low_temp


class CycleOffTime(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Cycle Off Time"
        self._attr_unique_id = f"{self.coordinator.state.id}_cycle_off_time"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_cycle_off_time(int(value * 60))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        if cycle_off_time := self.coordinator.state.cycle_off_time:
            self._attr_native_value = cycle_off_time / 60


class CycleOnTime(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Cycle On Time"
        self._attr_unique_id = f"{self.coordinator.state.id}_cycle_on_time"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_cycle_on_time(int(value * 60))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        if cycle_on_time := self.coordinator.state.cycle_on_time:
            self._attr_native_value = cycle_on_time / 60


class OnSpeed(ACIEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "On Fan Speed"
        self._attr_unique_id = f"{self.coordinator.state.id}_on_fan_speed"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_on_speed(int(value))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.coordinator.state.fan_speed_on


class OffSpeed(ACIEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 10
    _attr_native_step = 1

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Off Fan Speed"
        self._attr_unique_id = f"{self.coordinator.state.id}_off_fan_speed"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_off_speed(int(value))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        self._attr_native_value = self.coordinator.state.fan_speed_off


class TimerToOnTime(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Timer to On"
        self._attr_unique_id = f"{self.coordinator.state.id}_timer_to_on"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_timer_to_on(int(value * 60))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        if timer_to_on_time := self.coordinator.state.timer_to_on_time:
            self._attr_native_value = timer_to_on_time / 60


class TimerToOffTime(ACIEntity, NumberEntity):
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_device_class = NumberDeviceClass.DURATION
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0

    def __init__(self, coordinator: ACICoordinator):
        super().__init__(coordinator)
        self._attr_name = "Timer to Off"
        self._attr_unique_id = f"{self.coordinator.state.id}_timer_to_off"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.bt.set_timer_to_off(int(value * 60))

    @property
    def available(self) -> bool:  # type: ignore
        return self.coordinator.available

    @callback
    def _async_update_attrs(self) -> None:
        if timer_to_off_time := self.coordinator.state.timer_to_off_time:
            self._attr_native_value = timer_to_off_time / 60
