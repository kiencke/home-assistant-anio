"""Binary sensor platform for Anio watches."""

from typing import Any, override

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import AnioCoordinator
from .entity import get_device_info, get_device_setting


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Anio binary sensors."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AnioLocatingEnabledBinarySensor(device)
        for device in coordinator.devices
    )


class AnioLocatingEnabledBinarySensor(BinarySensorEntity):
    """Represent whether location reporting is enabled in the watch settings."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "locating_enabled"

    def __init__(self, device: dict[str, Any]) -> None:
        """Initialize the locating-enabled binary sensor."""
        super().__init__()
        self._device = device
        self._attr_unique_id = f"{device['id'].strip()}_locating_enabled"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def available(self) -> bool:
        """Only report availability when the API supplied a boolean setting."""
        return isinstance(get_device_setting(self._device, "isLocatingActive"), bool)

    @property
    @override
    def is_on(self) -> bool:
        """Return whether location reporting is enabled."""
        return get_device_setting(self._device, "isLocatingActive") is True
