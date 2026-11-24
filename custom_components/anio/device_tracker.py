"""Device tracker platform for Anio watches."""

from typing import Any, override

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnioCoordinator
from .entity import get_device_info, get_gps_accuracy, get_valid_position


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Anio watch trackers."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AnioTracker(coordinator, device) for device in coordinator.devices
    )


class AnioTracker(CoordinatorEntity[AnioCoordinator], TrackerEntity):
    """Represent an Anio watch location."""

    _attr_has_entity_name = True
    _attr_entity_category: EntityCategory | None = None
    _attr_source_type = SourceType.GPS
    _attr_translation_key = "location"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the tracker."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_location"
        self._attr_device_info = get_device_info(device)

    @property
    def _location(self) -> dict[str, Any] | None:
        """Return the latest location record for this watch."""
        return self.coordinator.data.get(self._device_id)

    @property
    def _position(self) -> tuple[float, float] | None:
        """Return a validated position for this watch."""
        location = self._location
        if location is None:
            return None
        return get_valid_position(location)

    @property
    @override
    def latitude(self) -> float | None:
        """Return the latest latitude."""
        position = self._position
        return position[0] if position is not None else None

    @property
    @override
    def longitude(self) -> float | None:
        """Return the latest longitude."""
        position = self._position
        return position[1] if position is not None else None

    @property
    @override
    def location_accuracy(self) -> float:
        """Return API accuracy when present; TrackerEntity requires a number."""
        accuracy = get_gps_accuracy(self._location)
        return float(accuracy) if accuracy is not None else 0.0
