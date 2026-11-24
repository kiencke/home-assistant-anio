"""Button platform for Anio watches."""

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnioCoordinator
from .entity import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up location-request buttons."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        entity
        for device in coordinator.devices
        for entity in (
            AnioLocationRequestButton(coordinator, device),
            AnioFindMyDeviceButton(coordinator, device),
        )
    )


class AnioLocationRequestButton(CoordinatorEntity[AnioCoordinator], ButtonEntity):
    """Request a one-time location update from an Anio watch."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:crosshairs-gps"
    _attr_translation_key = "location_request"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the location-request button."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_location_request"
        self._attr_device_info = get_device_info(device)

    async def async_press(self) -> None:
        """Ask the API to request a new location from the watch."""
        await self.coordinator.async_request_location_once(self._device_id)


class AnioFindMyDeviceButton(CoordinatorEntity[AnioCoordinator], ButtonEntity):
    """Ring an Anio watch after the safety guard is disabled."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:bell-ring-outline"
    _attr_translation_key = "find_my_device"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the Find My Device button."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_find_my_device"
        self._attr_device_info = get_device_info(device)

    async def async_press(self) -> None:
        """Ring the watch unless the default-on protection blocks the command."""
        await self.coordinator.async_find_device(self._device_id)
