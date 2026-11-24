"""Services for sending Anio chat emojis."""

from typing import Any

import probatio
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import AnioApiError
from .const import (
    ANIO_EMOJIS,
    DOMAIN,
    SERVICE_REFRESH_ACTIVITIES,
    SERVICE_REFRESH_CHAT,
    SERVICE_SEND_EMOJI,
)
from .coordinator import AnioCoordinator, supports_chat_emoji

_EMOJI_SERVICE_SCHEMA = probatio.Schema(
    {
        probatio.Required("device_id"): probatio.Any(cv.string, [cv.string]),
        probatio.Required("emoji_code"): cv.string,
    }
)
_REFRESH_CHAT_SERVICE_SCHEMA = probatio.Schema(
    {
        probatio.Required("device_id"): probatio.Any(cv.string, [cv.string]),
    }
)
_REFRESH_ACTIVITIES_SERVICE_SCHEMA = probatio.Schema(
    {
        probatio.Required("device_id"): probatio.Any(cv.string, [cv.string]),
        probatio.Optional("force", default=True): cv.boolean,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Register Anio services."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_EMOJI,
        async_send_emoji,
        schema=_EMOJI_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_CHAT,
        async_refresh_chat,
        schema=_REFRESH_CHAT_SERVICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_ACTIVITIES,
        async_refresh_activities,
        schema=_REFRESH_ACTIVITIES_SERVICE_SCHEMA,
    )


async def async_send_emoji(call: ServiceCall) -> None:
    """Send an API-coded emoji to one selected Anio watch."""
    target_ids = call.data["device_id"]
    if isinstance(target_ids, str):
        target_ids = [target_ids]
    if len(target_ids) != 1:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="one_watch_required",
        )

    registry_device = dr.async_get(call.hass).async_get(target_ids[0])
    if registry_device is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="ha_device_not_found",
        )

    anio_identifier = next(
        (
            identifier
            for identifier in registry_device.identifiers
            if identifier[0] == DOMAIN
        ),
        None,
    )
    if anio_identifier is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_anio_watch",
        )
    anio_device_id = anio_identifier[1]

    coordinator, device = _get_chat_emoji_target(call.hass, anio_device_id)
    if coordinator is None or device is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="emoji_chat_unavailable",
        )

    emoji_code = call.data["emoji_code"].strip()
    if emoji_code not in ANIO_EMOJIS:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="invalid_emoji_code",
        )

    try:
        await coordinator.async_send_chat_emoji(anio_device_id, emoji_code)
    except AnioApiError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="emoji_send_failed",
        ) from err


async def async_refresh_chat(call: ServiceCall) -> None:
    """Fetch new messages for one selected Anio watch."""
    anio_device_id = _selected_anio_device_id(call)
    coordinator = _get_chat_coordinator(call.hass, anio_device_id)
    if coordinator is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="chat_unavailable",
        )
    await coordinator.async_refresh_chat(anio_device_id)


async def async_refresh_activities(call: ServiceCall) -> None:
    """Refresh all activities for the selected watch's Anio account."""
    anio_device_id = _selected_anio_device_id(call)
    coordinator = next(
        (
            candidate
            for candidate in call.hass.data.get(DOMAIN, {}).values()
            if isinstance(candidate, AnioCoordinator)
            and anio_device_id in candidate.device_ids
        ),
        None,
    )
    if coordinator is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="activity_unavailable",
        )
    await coordinator.async_refresh_activities(force=call.data.get("force", True))


def _selected_anio_device_id(call: ServiceCall) -> str:
    """Resolve exactly one selected Home Assistant device to an Anio watch."""
    target_ids = call.data["device_id"]
    if isinstance(target_ids, str):
        target_ids = [target_ids]
    if len(target_ids) != 1:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="one_watch_required",
        )

    registry_device = dr.async_get(call.hass).async_get(target_ids[0])
    if registry_device is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="ha_device_not_found",
        )

    anio_identifier = next(
        (
            identifier
            for identifier in registry_device.identifiers
            if identifier[0] == DOMAIN
        ),
        None,
    )
    if anio_identifier is None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_anio_watch",
        )

    return anio_identifier[1]


def _get_chat_coordinator(
    hass: HomeAssistant, device_id: str
) -> AnioCoordinator | None:
    """Find the loaded coordinator responsible for one chat-enabled watch."""
    return next(
        (
            coordinator
            for coordinator in hass.data.get(DOMAIN, {}).values()
            if isinstance(coordinator, AnioCoordinator)
            and device_id in coordinator.chat_device_ids
        ),
        None,
    )


def _get_chat_emoji_target(
    hass: HomeAssistant, device_id: str
) -> tuple[AnioCoordinator | None, dict[str, Any] | None]:
    """Find the loaded coordinator and supported device metadata."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, AnioCoordinator):
            continue
        if device_id not in coordinator.device_ids:
            continue
        device = next(
            (
                device
                for device in coordinator.devices
                if isinstance(device.get("id"), str)
                and device["id"].strip() == device_id
                and supports_chat_emoji(device)
            ),
            None,
        )
        if device is not None:
            return coordinator, device
    return None, None
