"""Shared entity helpers for Anio."""

import math
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .api import AnioApiError
from .const import CHAT_USERNAME, DOMAIN


async def async_get_chat_sender(hass: HomeAssistant, context: Context | None) -> str:
    """Resolve the initiating user's name, or use the integration sender."""
    if context is not None and context.user_id:
        user = await hass.auth.async_get_user(context.user_id)
        if user is not None and user.name and user.name.strip():
            return user.name
    return CHAT_USERNAME


def get_device_info(device: dict[str, Any]) -> DeviceInfo:
    """Create registry information without exposing private API fields."""
    device_id = device.get("id")
    if not isinstance(device_id, str) or not device_id.strip():
        raise AnioApiError("Anio device is missing a valid id")
    device_id = device_id.strip()

    settings = device.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    config = device.get("config")
    if not isinstance(config, dict):
        config = {}

    name = settings.get("name")
    if not isinstance(name, str) or not name.strip():
        name = f"Anio Watch {device_id}"
    else:
        name = name.strip()

    model_parts: list[str] = []
    device_type = config.get("type")
    if isinstance(device_type, str) and device_type.strip():
        model_parts.append(device_type.strip())
    generation = config.get("generation")
    if isinstance(generation, (str, int)) and str(generation).strip():
        model_parts.append(f"Generation {generation}")

    firmware_version = config.get("firmwareVersion")
    if not isinstance(firmware_version, str):
        firmware_version = None

    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        manufacturer="Anio",
        name=name,
        model=" ".join(model_parts) or None,
        sw_version=firmware_version,
    )


def get_valid_position(location: dict[str, Any]) -> tuple[float, float] | None:
    """Return valid latitude and longitude from a location record."""
    position = location.get("position")
    if not isinstance(position, list) or len(position) < 2:
        return None

    latitude, longitude = position[:2]
    if (
        not isinstance(latitude, (int, float))
        or isinstance(latitude, bool)
        or not -90 <= latitude <= 90
        or not math.isfinite(latitude)
        or not isinstance(longitude, (int, float))
        or isinstance(longitude, bool)
        or not -180 <= longitude <= 180
        or not math.isfinite(longitude)
    ):
        return None

    return float(latitude), float(longitude)


def get_battery_level(location: dict[str, Any] | None) -> int | float | None:
    """Return a valid battery percentage if present."""
    return get_percentage(location, "batteryLevel")


def get_gps_accuracy(location: dict[str, Any] | None) -> int | float | None:
    """Return a non-negative, finite GPS accuracy value in meters."""
    value = get_location_number(location, "accuracy")
    return value if value is not None and value >= 0 else None


def get_location_number(
    location: dict[str, Any] | None, key: str
) -> int | float | None:
    """Return a finite numeric value from a location record."""
    if location is None:
        return None

    value = location.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def get_percentage(location: dict[str, Any] | None, key: str) -> int | float | None:
    """Return a numeric percentage if it is in the inclusive 0–100 range."""
    value = get_location_number(location, key)
    if value is None or not 0 <= value <= 100:
        return None
    return value


def get_device_setting(device: dict[str, Any], key: str) -> Any:
    """Return one setting from a device-list response."""
    settings = device.get("settings")
    if not isinstance(settings, dict):
        return None
    return settings.get(key)
