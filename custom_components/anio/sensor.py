"""Sensor platform for Anio watches."""

from datetime import datetime
from typing import Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    AnioChatMessage,
    AnioCoordinator,
    get_chat_audio_url,
    get_location_timestamp,
    supports_chat_incoming,
    supports_chat_text,
)
from .entity import (
    get_battery_level,
    get_device_info,
    get_gps_accuracy,
    get_location_number,
    get_percentage,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Anio battery sensors."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device in coordinator.devices:
        entities.extend(
            [
                AnioBatterySensor(coordinator, device),
                AnioTrackingModeSensor(coordinator, device),
                AnioLocationRequestStatusSensor(coordinator, device),
                AnioLocationTimestampSensor(
                    coordinator, device, "date", "last_location"
                ),
                AnioLocationTimestampSensor(
                    coordinator, device, "lastResponse", "last_response"
                ),
                AnioPositionSourceSensor(coordinator, device),
                AnioSignalStrengthSensor(coordinator, device),
                AnioGpsAccuracySensor(coordinator, device),
                AnioRawLocationNumberSensor(
                    coordinator, device, "speed", "mdi:speedometer"
                ),
                AnioRawLocationNumberSensor(
                    coordinator, device, "direction", "mdi:compass-outline"
                ),
                AnioRadarRemainingSensor(coordinator, device),
                AnioActivitySensor(coordinator, device),
            ]
        )
        if supports_chat_incoming(device) or supports_chat_text(device):
            entities.append(AnioLastChatMessageSensor(coordinator, device))
    async_add_entities(entities)


class AnioBatterySensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent an Anio watch battery level."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_battery"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> int | float | None:
        """Return the latest battery percentage."""
        return get_battery_level(self.coordinator.data.get(self._device_id))


class AnioTrackingModeSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent the tracking mode in the latest location record."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_has_entity_name = True
    _attr_options = ["normal", "schoolway", "explorer"]
    _attr_icon = "mdi:map-marker-path"
    _attr_translation_key = "tracking_mode"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the tracking-mode sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_tracking_mode"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> str | None:
        """Return a translated tracking mode from the latest location record."""
        mode = self.coordinator.tracking_mode(self._device_id)
        normalized_mode = mode.lower() if mode is not None else None
        return (
            normalized_mode
            if normalized_mode in {"normal", "schoolway", "explorer"}
            else None
        )


class AnioActivitySensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Expose the persisted activity history for one watch."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:timeline-clock-outline"
    _attr_translation_key = "last_activity"
    _unrecorded_attributes = frozenset({"activities"})

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the activity sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_last_activity"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def available(self) -> bool:
        """Keep activity history available independently of location polling."""
        return True

    @property
    @override
    def native_value(self) -> str | None:
        """Return the latest activity type."""
        activities = self.coordinator.activities(self._device_id)
        return activities[0].activity_type.lower()[:255] if activities else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return minimized activity details, including original timestamps."""
        return {
            "update_available": self.coordinator.activity_available(),
            "activities": [
                {
                    "id": item.activity_id,
                    "type": item.activity_type,
                    "text": item.text,
                    "zone": item.zone,
                    "timestamp": item.created_at.isoformat(),
                    "display_timestamp": item.display_time.isoformat(),
                }
                for item in self.coordinator.activities(self._device_id)
            ],
        }


class AnioLastChatMessageSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent the latest chat message and a short conversation history."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:message-text-outline"
    _attr_translation_key = "last_message"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the latest-chat-message sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_last_message"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def available(self) -> bool:
        """Return whether chat polling succeeded for this watch."""
        return self.coordinator.chat_available(self._device_id)

    @property
    @override
    def native_value(self) -> str | None:
        """Return the latest message content or a normalized type label."""
        message = self.coordinator.last_chat_message(self._device_id)
        return message.display_value if message is not None else None

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose safe metadata and the recent conversation for the dashboard."""
        message: AnioChatMessage | None = self.coordinator.last_chat_message(
            self._device_id
        )
        if message is None:
            return None
        attributes: dict[str, Any] = {
            "message_id": message.message_id,
            "message_type": message.message_type.lower(),
            "sender": message.sender.lower(),
            "timestamp": message.created_at.isoformat() if message.created_at else None,
            "is_from_watch": message.is_from_watch,
            "audio_url": (
                get_chat_audio_url(self._device_id, message.message_id)
                if message.message_type == "VOICE"
                else None
            ),
            "messages": [
                _chat_message_attributes(self._device_id, item)
                for item in self.coordinator.chat_messages(self._device_id)
            ],
        }
        if message.message_type in {"TEXT", "EMOJI"} and message.text is not None:
            attributes["message"] = message.text
        return attributes


class AnioLocationRequestStatusSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent progress of a user-requested location update."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_icon = "mdi:map-clock-outline"
    _attr_options = ["idle", "requesting", "updated", "timeout", "error"]
    _attr_translation_key = "location_request_status"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the location-request status sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_location_request_status"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> str:
        """Return whether a location request is pending or completed."""
        return self.coordinator.location_request_status(self._device_id)


class AnioLocationTimestampSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent a timestamp from the latest location record."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnioCoordinator,
        device: dict[str, Any],
        location_key: str,
        translation_key: str,
    ) -> None:
        """Initialize a location timestamp sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._location_key = location_key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{self._device_id}_{translation_key}"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> datetime | None:
        """Return the timestamp normalized to UTC."""
        location = (self.coordinator.data or {}).get(self._device_id)
        return get_location_timestamp(location, self._location_key)


class AnioPositionSourceSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent the source of the latest position."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_translation_key = "position_source"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the position-source sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_position_source"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> str | None:
        """Return the raw position source reported by the API."""
        location = (self.coordinator.data or {}).get(self._device_id)
        source = location.get("positionDeterminedBy") if location else None
        if not isinstance(source, str):
            return None
        return source.strip() or None

    @property
    @override
    def icon(self) -> str:
        """Use an icon for the reported positioning method when known."""
        if self.native_value == "GPS":
            return "mdi:satellite-variant"
        if self.native_value == "WIFI":
            return "mdi:wifi"
        return "mdi:map-marker"


class AnioSignalStrengthSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent cellular network quality as a percentage."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "signal_strength"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the signal-strength sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_signal_strength"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> int | float | None:
        """Return the cellular network quality percentage."""
        location = (self.coordinator.data or {}).get(self._device_id)
        return get_percentage(location, "signalStrength")

    @property
    @override
    def icon(self) -> str:
        """Show cellular signal bars based on the reported percentage."""
        value = self.native_value
        if value is None:
            return "mdi:signal-cellular-outline"
        if value < 34:
            return "mdi:signal-cellular-1"
        if value < 67:
            return "mdi:signal-cellular-2"
        return "mdi:signal-cellular-3"


class AnioRawLocationNumberSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent a raw numeric value from the latest location record."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AnioCoordinator,
        device: dict[str, Any],
        location_key: str,
        icon: str,
    ) -> None:
        """Initialize a raw numeric location sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._location_key = location_key
        self._attr_icon = icon
        self._attr_translation_key = location_key
        self._attr_unique_id = f"{self._device_id}_{location_key}"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> int | float | None:
        """Return a finite numeric value without assuming a unit."""
        location = (self.coordinator.data or {}).get(self._device_id)
        return get_location_number(location, self._location_key)


class AnioGpsAccuracySensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Represent GPS accuracy in meters as a diagnostic sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "gps_accuracy"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the GPS accuracy sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_gps_accuracy"
        self._attr_icon = "mdi:map-marker-radius"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> int | float | None:
        """Return the API accuracy, preserving zero and missing values."""
        return get_gps_accuracy((self.coordinator.data or {}).get(self._device_id))


class AnioRadarRemainingSensor(CoordinatorEntity[AnioCoordinator], SensorEntity):
    """Show the time left in the active Radar Mode session."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "radar_remaining"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the Radar Mode remaining-time sensor."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_radar_remaining"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def native_value(self) -> int | None:
        """Return remaining time rounded up to whole minutes."""
        seconds = self.coordinator.radar_remaining_seconds(self._device_id)
        return (seconds + 59) // 60 if seconds is not None else None


def _chat_message_attributes(
    device_id: str, message: AnioChatMessage
) -> dict[str, Any]:
    """Return one message without exposing any upstream audio URL."""
    return {
        "message_id": message.message_id,
        "sender": message.sender.lower(),
        "timestamp": message.created_at.isoformat() if message.created_at else None,
        "message_type": message.message_type.lower(),
        "message": (
            message.text if message.message_type in {"TEXT", "EMOJI"} else None
        ),
        "is_from_watch": message.is_from_watch,
        "audio_url": (
            get_chat_audio_url(device_id, message.message_id)
            if message.message_type == "VOICE"
            else None
        ),
    }
