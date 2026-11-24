"""Notify platform for Anio watches."""

from typing import Any, override

from homeassistant.components.notify import NotifyEntity
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
    """Set up a text notification entity for each chat-enabled watch."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AnioChatNotifyEntity(coordinator, device)
        for device in coordinator.devices
        if supports_chat_text(device)
    )


class AnioChatNotifyEntity(CoordinatorEntity[AnioCoordinator], NotifyEntity):
    """Send text messages to one Anio watch."""

    _attr_has_entity_name = True
    _attr_translation_key = "chat"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the per-watch notification entity."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._device = device
        self._attr_unique_id = f"{self._device_id}_chat"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def available(self) -> bool:
        """Allow sending independently of location polling."""
        return True

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a text message after validating the watch's character limit."""
        if not message.strip():
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_empty",
            )

        max_length = get_chat_max_length(self._device)
        if max_length is not None and len(message) > max_length:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_too_long",
                translation_placeholders={"max_length": str(max_length)},
            )

        sender_name = await async_get_chat_sender(self.hass, self._context)
        try:
            await self.coordinator.async_send_chat_text(
                self._device_id, message, username=sender_name
            )
        except AnioApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="message_send_failed",
            ) from err
