"""Text platform for Anio watches."""

from typing import Any, override

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AnioApiError
from .const import DOMAIN
from .coordinator import AnioCoordinator, get_chat_max_length, supports_chat_text
from .entity import async_get_chat_sender, get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one native text entity for each text-chat-enabled watch."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AnioChatTextEntity(coordinator, device)
        for device in coordinator.devices
        if supports_chat_text(device)
    )


class AnioChatTextEntity(CoordinatorEntity[AnioCoordinator], TextEntity):
    """Send text messages when the user confirms a value."""

    _attr_has_entity_name = True
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_translation_key = "send_message"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the per-watch text entity."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        max_length = get_chat_max_length(device) or 255
        self._attr_native_max = min(max_length, 255)
        self._attr_native_value = ""
        self._attr_unique_id = f"{self._device_id}_send_message"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> str:
        """Return the current draft without caching it between sends."""
        return self._attr_native_value or ""

    @property
    @override
    def available(self) -> bool:
        """Allow sending independently of location polling."""
        return True

    @override
    async def async_set_value(self, value: str) -> None:
        """Send a non-empty value and clear the entity after success."""
        if not value.strip():
            self._attr_native_value = ""
            self.async_write_ha_state()
            return

        if len(value) > self._attr_native_max:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_too_long",
                translation_placeholders={
                    "max_length": str(self._attr_native_max),
                },
            )

        sender_name = await async_get_chat_sender(self.hass, self._context)
        self._attr_native_value = value
        self.async_write_ha_state()
        try:
            await self.coordinator.async_send_chat_text(
                self._device_id, value, username=sender_name
            )
        except AnioApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_send_failed",
            ) from err

        self._attr_native_value = ""
        self.async_write_ha_state()
