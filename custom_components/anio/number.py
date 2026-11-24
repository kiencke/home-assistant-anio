"""Number platform for Anio Radar Mode settings."""

import logging
import math
from typing import Any, override

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    RADAR_MAX_DURATION_MINUTES,
    RADAR_MAX_INTERVAL_SECONDS,
    RADAR_MIN_DURATION_MINUTES,
    RADAR_MIN_INTERVAL_SECONDS,
)
from .coordinator import AnioCoordinator
from .entity import get_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Radar Mode configuration numbers."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        entity
        for device in coordinator.devices
        for entity in (
            AnioRadarDurationNumber(coordinator, device),
            AnioRadarIntervalNumber(coordinator, device),
        )
    )


class AnioRadarNumber(CoordinatorEntity[AnioCoordinator], RestoreNumber):
    """Base number for one Radar Mode setting."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the per-watch Radar Mode number."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> float:
        """Return the configured setting."""
        return float(self._get_value())

    async def async_added_to_hass(self) -> None:
        """Restore a prior valid setting, otherwise retain its safe default."""
        await super().async_added_to_hass()
        restored = await self.async_get_last_number_data()
        if restored is None or restored.native_value is None:
            return
        value = restored.native_value
        if not _is_valid_setting(value, self._minimum, self._maximum):
            _LOGGER.warning("Ignoring an invalid restored Radar Mode setting")
            return
        self._set_value(int(value))
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set a valid integer setting for the next Radar Mode session."""
        if not _is_valid_setting(value, self._minimum, self._maximum):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="radar_value_out_of_range",
                translation_placeholders={
                    "minimum": str(self._minimum),
                    "maximum": str(self._maximum),
                },
            )
        self._set_value(int(value))
        self.async_write_ha_state()

    def _get_value(self) -> int:
        raise NotImplementedError

    def _set_value(self, value: int) -> None:
        raise NotImplementedError

    @property
    def _minimum(self) -> int:
        raise NotImplementedError

    @property
    def _maximum(self) -> int:
        raise NotImplementedError


def _is_valid_setting(value: object, minimum: int, maximum: int) -> bool:
    """Return whether a setting is a finite integer within its bounds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        numeric_value = float(value)
    except OverflowError:
        return False
    return (
        math.isfinite(numeric_value)
        and numeric_value.is_integer()
        and minimum <= numeric_value <= maximum
    )


class AnioRadarDurationNumber(AnioRadarNumber):
    """Configure the Radar Mode duration."""

    _attr_icon = "mdi:timer-outline"
    _attr_native_max_value = RADAR_MAX_DURATION_MINUTES
    _attr_native_min_value = RADAR_MIN_DURATION_MINUTES
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_translation_key = "radar_duration"

    @property
    def _minimum(self) -> int:
        return RADAR_MIN_DURATION_MINUTES

    @property
    def _maximum(self) -> int:
        return RADAR_MAX_DURATION_MINUTES

    def _get_value(self) -> int:
        return self.coordinator.radar_duration(self._device_id)

    def _set_value(self, value: int) -> None:
        self.coordinator.set_radar_duration(self._device_id, value)


class AnioRadarIntervalNumber(AnioRadarNumber):
    """Configure the interval between Radar Mode requests."""

    _attr_icon = "mdi:timer-cog-outline"
    _attr_native_max_value = RADAR_MAX_INTERVAL_SECONDS
    _attr_native_min_value = RADAR_MIN_INTERVAL_SECONDS
    _attr_native_step = 30
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_translation_key = "radar_interval"

    @property
    def _minimum(self) -> int:
        return RADAR_MIN_INTERVAL_SECONDS

    @property
    def _maximum(self) -> int:
        return RADAR_MAX_INTERVAL_SECONDS

    def _get_value(self) -> int:
        return self.coordinator.radar_interval(self._device_id)

    def _set_value(self, value: int) -> None:
        self.coordinator.set_radar_interval(self._device_id, value)
