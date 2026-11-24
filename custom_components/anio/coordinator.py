"""Coordinators for Anio watch data."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import ceil
from time import monotonic
from typing import Any, override
from urllib.parse import quote

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    AnioApi,
    AnioApiError,
    AnioAuthError,
    AnioConnectionError,
    AnioRateLimitError,
)
from .const import (
    CHAT_USERNAME,
    CONF_ACTIVITY_INTERVAL,
    DEFAULT_ACTIVITY_INTERVAL_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_CHAT_MESSAGE_RECEIVED,
    MAX_ACTIVITY_INTERVAL_MINUTES,
    MIN_ACTIVITY_INTERVAL_MINUTES,
    RADAR_DEFAULT_DURATION_MINUTES,
    RADAR_DEFAULT_INTERVAL_SECONDS,
    RADAR_LOCATION_WAIT_SECONDS,
    RADAR_MAX_DURATION_MINUTES,
    RADAR_MAX_INTERVAL_SECONDS,
    RADAR_MIN_BATTERY_PERCENT,
    RADAR_MIN_DURATION_MINUTES,
    RADAR_MIN_INTERVAL_SECONDS,
    TRACKING_MODES,
)
from .entity import get_battery_level

_LOGGER = logging.getLogger(__name__)
CHAT_INITIAL_SINCE = datetime(2000, 1, 1, tzinfo=UTC)
CHAT_POLL_OVERLAP = timedelta(minutes=1)
CHAT_STORAGE_VERSION = 1
ACTIVITY_AUTO_REFRESH_COOLDOWN = 30


@dataclass
class LocationRequest:
    """Track the result of a user-requested location update."""

    requested_at: datetime
    baseline_date: datetime | None
    deadline: datetime
    status: str = "requesting"


@dataclass
class RadarSession:
    """Track one bounded Radar Mode session."""

    started_at: datetime
    deadline: datetime
    interval_seconds: int
    task: asyncio.Task[None] | None = None


@dataclass(frozen=True)
class AnioChatMessage:
    """A normalized Anio chat message."""

    message_id: str
    message_type: str
    sender: str
    text: str | None
    created_at: datetime | None

    @property
    def is_from_watch(self) -> bool:
        """Return whether the message was sent by the watch."""
        return self.sender == "DEVICE"

    @property
    def display_value(self) -> str:
        """Return text content or a type label suitable for a sensor state."""
        if self.message_type in {"TEXT", "EMOJI"} and self.text:
            return self.text[:255]
        return self.message_type.lower()


@dataclass(frozen=True)
class AnioActivity:
    """A minimized activity record with its original timestamp."""

    activity_id: str
    activity_type: str
    text: str
    zone: str | None
    created_at: datetime

    @property
    def display_time(self) -> datetime:
        """Round to seconds and adjust departure times for display."""
        rounded = (self.created_at + timedelta(microseconds=500000)).replace(
            microsecond=0
        )
        if self.activity_type == "GEOFENCE_LEFT":
            return rounded - timedelta(minutes=1)
        return rounded


class AnioCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch the latest location data and associate it with watches."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AnioApi,
        config_entry: ConfigEntry,
        devices: list[dict[str, Any]],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.devices = devices
        self.chat_device_ids = {
            device["id"].strip()
            for device in devices
            if isinstance(device.get("id"), str)
            and device["id"].strip()
            and (supports_chat_text(device) or supports_chat_incoming(device))
        }
        self.device_ids = {
            device["id"].strip()
            for device in devices
            if isinstance(device.get("id"), str) and device["id"].strip()
        }
        self.mode_intervals = {
            mode: _read_interval(config_entry.options.get(option))
            for mode, option in TRACKING_MODES.items()
        }
        self._location_requests: dict[str, LocationRequest] = {}
        self._explorer_overrides: dict[str, bool] = {}
        self._api_lock = asyncio.Lock()
        self._chat_lock = asyncio.Lock()
        self._chat_poll_task: asyncio.Task[None] | None = None
        self._chat_store = Store(
            hass,
            CHAT_STORAGE_VERSION,
            f"{DOMAIN}_{config_entry.entry_id}_chat_history",
            private=True,
        )
        self._chat_since = {
            device_id: CHAT_INITIAL_SINCE for device_id in self.chat_device_ids
        }
        self._chat_initialized: set[str] = set()
        self._chat_available: dict[str, bool] = {}
        self._last_chat_messages: dict[str, AnioChatMessage] = {}
        self._chat_history: dict[str, list[AnioChatMessage]] = {}
        self._chat_message_id_sets: dict[str, set[str]] = {}
        self._activity_store = Store(
            hass, 1, f"{DOMAIN}_{config_entry.entry_id}_activity_history", private=True
        )
        self._activity_history: dict[str, dict[str, AnioActivity]] = {}
        self._activity_available = False
        self._activity_dirty = False
        self._activity_refresh_task: asyncio.Task[None] | None = None
        self._activity_last_started: float | None = None
        interval = config_entry.options.get(
            CONF_ACTIVITY_INTERVAL, DEFAULT_ACTIVITY_INTERVAL_MINUTES
        )
        if (
            not isinstance(interval, int)
            or isinstance(interval, bool)
            or not MIN_ACTIVITY_INTERVAL_MINUTES
            <= interval
            <= MAX_ACTIVITY_INTERVAL_MINUTES
        ):
            _LOGGER.warning("Invalid activity interval; using 60 minutes")
            interval = DEFAULT_ACTIVITY_INTERVAL_MINUTES
        self.activity_interval = timedelta(minutes=interval)
        self._radar_sessions: dict[str, RadarSession] = {}
        self._radar_durations = {
            device_id: RADAR_DEFAULT_DURATION_MINUTES for device_id in self.device_ids
        }
        self._radar_intervals = {
            device_id: RADAR_DEFAULT_INTERVAL_SECONDS for device_id in self.device_ids
        }
        self._bell_protection = {device_id: True for device_id in self.device_ids}

    async def async_load_chat_history(self) -> None:
        """Restore persisted chat history and cursors before the first poll."""
        stored = await self._chat_store.async_load()
        if not isinstance(stored, dict):
            return

        stored_devices = stored.get("devices")
        if not isinstance(stored_devices, dict):
            _LOGGER.warning("Ignoring malformed persisted Anio chat history")
            return

        for device_id in self.chat_device_ids:
            device_data = stored_devices.get(device_id)
            if not isinstance(device_data, dict):
                continue

            since_value = device_data.get("since")
            since = (
                dt_util.parse_datetime(since_value)
                if isinstance(since_value, str)
                else None
            )
            if since is not None:
                self._chat_since[device_id] = dt_util.as_utc(since)

            records = device_data.get("messages", [])
            if not isinstance(records, list):
                _LOGGER.warning(
                    "Ignoring malformed persisted Anio chat messages for a device"
                )
                continue

            for record in records:
                if not isinstance(record, dict):
                    continue
                message = _parse_chat_message(record)
                if message is None or not self._remember_chat_message_id(
                    device_id, message.message_id
                ):
                    continue
                self._remember_chat_message(device_id, message)
                self._update_last_chat_message(device_id, message)

            self._chat_initialized.add(device_id)

    async def async_load_activity_history(self) -> None:
        """Restore activity records without exposing location coordinates."""
        stored = await self._activity_store.async_load()
        if stored is None:
            return
        if not isinstance(stored, dict) or not isinstance(stored.get("devices"), dict):
            _LOGGER.warning("Ignoring malformed persisted Anio activity history")
            return
        for device_id, records in stored["devices"].items():
            if not isinstance(device_id, str) or not isinstance(records, list):
                _LOGGER.warning("Ignoring malformed persisted Anio activity records")
                continue
            for record in records:
                if not isinstance(record, dict):
                    _LOGGER.warning("Ignoring malformed persisted Anio activity")
                    continue
                activity = _parse_activity(record)
                if activity is not None:
                    self._activity_history.setdefault(device_id, {})[
                        activity.activity_id
                    ] = activity

    @override
    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch locations and map each record to its Anio device ID."""
        try:
            async with self._api_lock:
                locations = await self.api.async_get_last_locations()
        except AnioAuthError as err:
            raise ConfigEntryAuthFailed("Anio access token is invalid") from err
        except AnioConnectionError as err:
            raise UpdateFailed("Could not connect to the Anio API") from err
        except AnioApiError as err:
            raise UpdateFailed("Anio returned an invalid location response") from err

        mapped_locations = map_locations_to_devices(locations, self.device_ids)
        self._update_location_requests(mapped_locations)
        self._update_explorer_states(mapped_locations)
        self._set_update_interval(mapped_locations)
        self._schedule_chat_poll()
        return mapped_locations

    def _schedule_chat_poll(self) -> None:
        """Start the regular chat poll without delaying a location update."""
        if not self.chat_device_ids or (
            self._chat_poll_task is not None and not self._chat_poll_task.done()
        ):
            return
        assert self.config_entry is not None
        self._chat_poll_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_run_chat_poll(),
            name=f"{DOMAIN} chat poll",
            eager_start=False,
        )

    async def _async_run_chat_poll(self) -> None:
        """Run a location-triggered chat poll independently of location updates."""
        try:
            await self._async_update_chat_messages()
        except (OSError, HomeAssistantError) as err:
            for device_id in self.chat_device_ids:
                self._chat_available[device_id] = False
            _LOGGER.warning("Anio chat polling failed (%s)", type(err).__name__)
        finally:
            self.async_update_listeners()

    def activity_available(self) -> bool:
        """Return whether the latest activity poll and save succeeded."""
        return self._activity_available

    async def async_refresh_activities(self, *, force: bool = True) -> None:
        """Share concurrent account-wide refreshes and throttle automatic openings."""
        task = self._activity_refresh_task
        if task is None or task.done():
            if (
                not force
                and self._activity_last_started is not None
                and monotonic() - self._activity_last_started
                < ACTIVITY_AUTO_REFRESH_COOLDOWN
            ):
                if not self._activity_available:
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="activity_refresh_failed",
                    )
                return
            self._activity_last_started = monotonic()
            task = self.hass.async_create_task(self._async_run_activity_refresh())
            self._activity_refresh_task = task
        try:
            await asyncio.shield(task)
        finally:
            if task.done() and self._activity_refresh_task is task:
                self._activity_refresh_task = None
        if not self._activity_available:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="activity_refresh_failed",
            )

    async def _async_run_activity_refresh(self) -> None:
        """Update activity entities without altering the location poll schedule."""
        try:
            await self._async_update_activities()
        finally:
            self.async_update_listeners()

    async def async_scheduled_activity_refresh(
        self, _now: datetime | None = None
    ) -> None:
        """Refresh on startup or on the independent schedule."""
        try:
            await self.async_refresh_activities()
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Scheduled Anio activity refresh failed (%s)", type(err).__name__
            )

    def async_cancel_activity_refresh(self) -> None:
        """Cancel an in-flight activity refresh during entry unload."""
        if self._activity_refresh_task is not None:
            self._activity_refresh_task.cancel()

    def activities(self, device_id: str) -> list[AnioActivity]:
        """Return a watch's activities newest first using adjusted display times."""
        return sorted(
            self._activity_history.get(device_id, {}).values(),
            key=lambda item: (
                item.display_time,
                item.activity_type == "GEOFENCE_ENTERED",
                item.created_at,
                item.activity_id,
            ),
            reverse=True,
        )

    async def _async_update_activities(self) -> None:
        """Poll activities independently of location and retain new records."""
        try:
            async with self._api_lock:
                records = await self.api.async_get_activities()
        except AnioApiError as err:
            self._activity_available = False
            _LOGGER.warning("Anio activity polling failed (%s)", type(err).__name__)
            return

        for record in records:
            device_id = record.get("deviceId")
            if not isinstance(device_id, str) or device_id not in self.device_ids:
                _LOGGER.warning("Ignoring an Anio activity with an unknown device")
                continue
            activity = _parse_activity(record)
            if activity is None:
                continue
            history = self._activity_history.setdefault(device_id, {})
            if activity.activity_id not in history:
                history[activity.activity_id] = activity
                self._activity_dirty = True

        if self._activity_dirty:
            data = {
                "devices": {
                    device_id: [
                        {
                            "id": item.activity_id,
                            "type": item.activity_type,
                            "text": item.text,
                            "zone": item.zone,
                            "createdAt": item.created_at.isoformat(),
                        }
                        for item in history.values()
                    ]
                    for device_id, history in self._activity_history.items()
                }
            }
            try:
                await self._activity_store.async_save(data)
                # Store logs certain write failures instead of raising them.
                if await self._activity_store.async_load() != data:
                    _LOGGER.warning("Could not verify saved Anio activity history")
                    self._activity_available = False
                    return
            except (OSError, HomeAssistantError) as err:
                self._activity_available = False
                _LOGGER.warning(
                    "Could not save Anio activity history (%s)", type(err).__name__
                )
                return
            self._activity_dirty = False
        self._activity_available = True

    def chat_available(self, device_id: str) -> bool:
        """Return whether the latest chat request for a watch succeeded."""
        return self._chat_available.get(device_id, False)

    def last_chat_message(self, device_id: str) -> AnioChatMessage | None:
        """Return the latest chat message for a watch."""
        return self._last_chat_messages.get(device_id)

    def chat_messages(self, device_id: str) -> list[AnioChatMessage]:
        """Return all stored chat messages in chronological order."""
        return list(self._chat_history.get(device_id, ()))

    def chat_message(self, device_id: str, message_id: str) -> AnioChatMessage | None:
        """Find a recent chat message by ID."""
        return next(
            (
                message
                for message in self._chat_history.get(device_id, ())
                if message.message_id == message_id
            ),
            None,
        )

    async def async_send_chat_text(
        self, device_id: str, text: str, *, username: str = CHAT_USERNAME
    ) -> None:
        """Send a text message to a watch using the supplied sender name."""
        async with self._api_lock:
            await self.api.async_send_chat_text(
                device_id,
                username=username,
                text=text,
            )
        await self._async_refresh_chat_after_send(device_id)

    async def async_send_chat_emoji(self, device_id: str, emoji_code: str) -> None:
        """Send an emoji code to a watch using the integration username."""
        async with self._api_lock:
            await self.api.async_send_chat_emoji(
                device_id,
                username=CHAT_USERNAME,
                emoji_code=emoji_code,
            )
        await self._async_refresh_chat_after_send(device_id)

    async def _async_refresh_chat_after_send(self, device_id: str) -> None:
        """Refresh after sending without turning a refresh failure into send failure."""
        try:
            await self.async_refresh_chat(device_id)
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Anio message was sent but its immediate chat refresh failed (%s)",
                type(err).__name__,
            )

    async def async_refresh_chat(self, device_id: str) -> None:
        """Refresh one watch's chat without refreshing location data."""
        await self._async_update_chat_messages({device_id})
        self.async_update_listeners()
        if not self.chat_available(device_id):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="chat_refresh_failed",
            )

    async def _async_update_chat_messages(
        self, device_ids: set[str] | None = None
    ) -> None:
        """Serialize chat fetches and persistence across all refresh triggers."""
        async with self._chat_lock:
            await self._async_poll_chat_messages(device_ids)

    async def _async_poll_chat_messages(self, device_ids: set[str] | None) -> None:
        """Poll chats and persist any updates."""
        updated = False
        targets = (
            device_ids
            if device_ids is not None
            else getattr(self, "chat_device_ids", set())
        )
        for device_id in targets:
            poll_started = dt_util.utcnow()
            since = self._chat_since.get(device_id, CHAT_INITIAL_SINCE)
            try:
                async with self._api_lock:
                    messages = await self.api.async_get_chat_messages(
                        device_id, since=since
                    )
            except AnioApiError as err:
                self._chat_available[device_id] = False
                _LOGGER.warning(
                    "Anio chat polling failed; it will retry on the next update (%s)",
                    type(err).__name__,
                )
                continue

            self._chat_available[device_id] = True
            self._chat_since[device_id] = max(
                self._chat_since.get(device_id, CHAT_INITIAL_SINCE),
                poll_started - CHAT_POLL_OVERLAP,
            )
            updated = True
            first_successful_poll = device_id not in self._chat_initialized
            for record in messages:
                message = _parse_chat_message(record)
                if message is None:
                    continue
                if not self._remember_chat_message_id(device_id, message.message_id):
                    continue

                self._remember_chat_message(device_id, message)
                self._update_last_chat_message(device_id, message)

                if not first_successful_poll and message.is_from_watch:
                    self.hass.bus.async_fire(
                        EVENT_CHAT_MESSAGE_RECEIVED,
                        _chat_event_data(device_id, message),
                    )

            self._chat_initialized.add(device_id)

        if updated:
            await self._async_save_chat_history()

    def _remember_chat_message(self, device_id: str, message: AnioChatMessage) -> None:
        """Keep all messages in chronological order for the chat sensor."""
        history = self._chat_history.setdefault(device_id, [])
        oldest = datetime.min.replace(tzinfo=UTC)
        history.append(message)
        history.sort(
            key=lambda item: item.created_at or oldest,
        )

    def _remember_chat_message_id(self, device_id: str, message_id: str) -> bool:
        """Remember a message ID and return whether it has not been seen before."""
        known_ids = self._chat_message_id_sets.setdefault(device_id, set())
        if message_id in known_ids:
            return False
        known_ids.add(message_id)
        return True

    def _update_last_chat_message(
        self, device_id: str, message: AnioChatMessage
    ) -> None:
        """Update the sensor state only when a message is as new as the current one."""
        current_message = self._last_chat_messages.get(device_id)
        if (
            current_message is None
            or (current_message.created_at is None and message.created_at is not None)
            or (
                current_message.created_at is not None
                and message.created_at is not None
                and message.created_at >= current_message.created_at
            )
            or (current_message.created_at is None and message.created_at is None)
        ):
            self._last_chat_messages[device_id] = message

    async def _async_save_chat_history(self) -> None:
        """Persist each watch's cursor and complete message history."""
        await self._chat_store.async_save(
            {
                "devices": {
                    device_id: {
                        "since": self._chat_since[device_id].isoformat(),
                        "messages": [
                            {
                                "id": message.message_id,
                                "type": message.message_type,
                                "sender": message.sender,
                                "text": message.text,
                                "createdAt": (
                                    message.created_at.isoformat()
                                    if message.created_at
                                    else None
                                ),
                            }
                            for message in self._chat_history.get(device_id, [])
                        ],
                    }
                    for device_id in self.chat_device_ids
                }
            }
        )

    def tracking_mode(self, device_id: str) -> str | None:
        """Return the last mode reported with the watch's latest location."""
        location = (self.data or {}).get(device_id)
        mode = location.get("trackingMode") if location else None
        if not isinstance(mode, str):
            return None
        return mode.strip() or None

    def explorer_active(self, device_id: str) -> bool | None:
        """Return the latest known Explorer state, if it can be determined."""
        if device_id in self._explorer_overrides:
            return self._explorer_overrides[device_id]
        return self._reported_explorer_active(device_id)

    def _reported_explorer_active(self, device_id: str) -> bool | None:
        """Infer Explorer state from the last location record."""
        mode = self.tracking_mode(device_id)
        if mode == "EXPLORER":
            return True
        if mode in ("NORMAL", "SCHOOLWAY"):
            return False
        return None

    def location_request_status(self, device_id: str) -> str:
        """Return the current status of a user-requested location update."""
        request = self._location_requests.get(device_id)
        return request.status if request else "idle"

    async def async_request_location_once(self, device_id: str) -> None:
        """Ask the watch for a location update and monitor for a newer fix."""
        now = dt_util.utcnow()
        location = (self.data or {}).get(device_id)
        baseline_date = get_location_timestamp(location, "date")
        timeout = 2 * self.update_interval.total_seconds()
        self._location_requests[device_id] = LocationRequest(
            requested_at=now,
            baseline_date=baseline_date,
            deadline=now + timedelta(seconds=timeout),
        )
        self._notify_entities()

        try:
            async with self._api_lock:
                await self.api.async_request_location_once(device_id)
        except AnioApiError:
            self._location_requests[device_id].status = "error"
            self._notify_entities()
            raise

        await self.async_request_refresh()

    async def async_set_explorer(self, device_id: str, *, activate: bool) -> None:
        """Set Explorer state and retain the API-confirmed result."""
        async with self._api_lock:
            response = await self.api.async_set_explorer(device_id, activate=activate)
        active = response["active"]
        if self._reported_explorer_active(device_id) != active:
            self._explorer_overrides[device_id] = active
        else:
            self._explorer_overrides.pop(device_id, None)
        previous_interval = self.update_interval
        self._set_update_interval(self.data or {})
        if self.update_interval != previous_interval and self._listeners:
            self._schedule_refresh()
        self._notify_entities()

    def bell_protection_enabled(self, device_id: str) -> bool:
        """Return whether Find My Device is blocked by its default safety guard."""
        return self._bell_protection.get(device_id, True)

    def set_bell_protection(self, device_id: str, enabled: bool) -> None:
        """Set the local Find My Device safety guard."""
        self._bell_protection[device_id] = enabled

    async def async_find_device(self, device_id: str) -> None:
        """Ring a watch after its safety guard has been deliberately disabled."""
        if self.bell_protection_enabled(device_id):
            _LOGGER.warning(
                "Blocked Find My Device because the bell protection is active"
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="bell_protection_active",
            )
        async with self._api_lock:
            await self.api.async_find_device(device_id)

    def radar_duration(self, device_id: str) -> int:
        """Return the configured Radar Mode duration in minutes."""
        return self._radar_durations.get(device_id, RADAR_DEFAULT_DURATION_MINUTES)

    def set_radar_duration(self, device_id: str, minutes: int) -> None:
        """Set a valid Radar Mode duration in minutes."""
        if (
            isinstance(minutes, bool)
            or not isinstance(minutes, int)
            or not RADAR_MIN_DURATION_MINUTES <= minutes <= RADAR_MAX_DURATION_MINUTES
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="radar_duration_out_of_range",
                translation_placeholders={
                    "minimum": str(RADAR_MIN_DURATION_MINUTES),
                    "maximum": str(RADAR_MAX_DURATION_MINUTES),
                },
            )
        self._radar_durations[device_id] = minutes

    def radar_interval(self, device_id: str) -> int:
        """Return the configured Radar Mode interval in seconds."""
        return self._radar_intervals.get(device_id, RADAR_DEFAULT_INTERVAL_SECONDS)

    def set_radar_interval(self, device_id: str, seconds: int) -> None:
        """Set a valid Radar Mode interval in seconds."""
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or not RADAR_MIN_INTERVAL_SECONDS <= seconds <= RADAR_MAX_INTERVAL_SECONDS
        ):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="radar_interval_out_of_range",
                translation_placeholders={
                    "minimum": str(RADAR_MIN_INTERVAL_SECONDS),
                    "maximum": str(RADAR_MAX_INTERVAL_SECONDS),
                },
            )
        self._radar_intervals[device_id] = seconds

    def radar_active(self, device_id: str) -> bool:
        """Return whether Radar Mode is running for a watch."""
        return device_id in self._radar_sessions

    def radar_remaining_seconds(self, device_id: str) -> int | None:
        """Return the rounded-up remaining Radar Mode time in seconds."""
        session = self._radar_sessions.get(device_id)
        if session is None:
            return None
        return max(0, ceil((session.deadline - dt_util.utcnow()).total_seconds()))

    async def async_start_radar(self, device_id: str) -> None:
        """Start a bounded Radar Mode session for a watch."""
        if device_id in self._radar_sessions:
            return

        battery = get_battery_level((self.data or {}).get(device_id))
        if battery is None or battery < RADAR_MIN_BATTERY_PERCENT:
            _LOGGER.warning(
                "Radar Mode start blocked because battery is unknown or below %s%%",
                RADAR_MIN_BATTERY_PERCENT,
            )
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="radar_battery_requirement",
                translation_placeholders={
                    "minimum": str(RADAR_MIN_BATTERY_PERCENT),
                },
            )

        started_at = dt_util.utcnow()
        session = RadarSession(
            started_at=started_at,
            deadline=started_at + timedelta(minutes=self.radar_duration(device_id)),
            interval_seconds=self.radar_interval(device_id),
        )
        self._radar_sessions[device_id] = session
        session.task = self.hass.async_create_task(
            self._async_run_radar(device_id, session),
            name=f"{DOMAIN} Radar Mode",
        )
        self._notify_entities()

    async def async_stop_radar(self, device_id: str) -> None:
        """Stop Radar Mode and cancel its outstanding cycle."""
        session = self._radar_sessions.pop(device_id, None)
        if session is None:
            return
        if session.task is not None:
            session.task.cancel()
            try:
                await session.task
            except asyncio.CancelledError:
                pass
        self._notify_entities()

    @override
    async def async_shutdown(self) -> None:
        """Cancel Radar Mode tasks before shutting down the coordinator."""
        sessions = list(self._radar_sessions.values())
        self._radar_sessions.clear()
        for session in sessions:
            if session.task is not None:
                session.task.cancel()
        for session in sessions:
            if session.task is not None:
                try:
                    await session.task
                except asyncio.CancelledError:
                    pass
        await super().async_shutdown()

    async def _async_run_radar(self, device_id: str, session: RadarSession) -> None:
        """Request locations serially until the timer or a safety condition ends."""
        try:
            while self._radar_sessions.get(device_id) is session:
                remaining = (session.deadline - dt_util.utcnow()).total_seconds()
                if remaining <= 0:
                    break

                cycle_started = monotonic()
                try:
                    await asyncio.wait_for(
                        self._async_radar_cycle(device_id),
                        timeout=remaining,
                    )
                except TimeoutError:
                    _LOGGER.info("Radar Mode stopped at its hard timeout")
                    break

                battery = get_battery_level((self.data or {}).get(device_id))
                if battery is None or battery < RADAR_MIN_BATTERY_PERCENT:
                    _LOGGER.warning(
                        "Radar Mode stopped because battery is unknown or below %s%%",
                        RADAR_MIN_BATTERY_PERCENT,
                    )
                    break

                self._notify_entities()
                remaining = (session.deadline - dt_util.utcnow()).total_seconds()
                sleep_seconds = min(
                    max(0, session.interval_seconds - (monotonic() - cycle_started)),
                    max(0, remaining),
                )
                if sleep_seconds:
                    await asyncio.sleep(sleep_seconds)
        except AnioRateLimitError as err:
            _LOGGER.warning("Radar Mode stopped after API rate limiting: %s", err)
        except (AnioAuthError, AnioConnectionError, AnioApiError) as err:
            _LOGGER.warning("Radar Mode stopped after an API error: %s", err)
        finally:
            if self._radar_sessions.get(device_id) is session:
                self._radar_sessions.pop(device_id)
                self._notify_entities()

    async def _async_radar_cycle(self, device_id: str) -> None:
        """Request a location, briefly wait, then refresh all device locations."""
        async with self._api_lock:
            await self.api.async_request_location_once(device_id)

        await asyncio.sleep(RADAR_LOCATION_WAIT_SECONDS)
        await self.async_refresh()
        if not self.last_update_success:
            error: BaseException | None = self.last_exception
            while error is not None:
                if isinstance(error, AnioApiError):
                    raise error
                error = error.__cause__
            raise AnioApiError("Radar Mode could not refresh the latest location")

    def _notify_entities(self) -> None:
        """Update entities after a command without forcing another API request."""
        if self.data is not None:
            self.async_update_listeners()

    def _set_update_interval(self, locations: dict[str, dict[str, Any]]) -> None:
        """Use the shortest configured interval for all known watch modes."""
        seconds = get_poll_interval_seconds(
            locations,
            self.mode_intervals,
            self.device_ids,
            self._explorer_overrides,
        )
        self.update_interval = timedelta(seconds=seconds)

    def _update_location_requests(self, locations: dict[str, dict[str, Any]]) -> None:
        """Mark requests complete on a newer position date or after timeout."""
        now = dt_util.utcnow()
        for device_id, request in self._location_requests.items():
            if request.status != "requesting":
                continue

            location = locations.get(device_id)
            current_date = get_location_timestamp(location, "date")
            if current_date is not None and (
                current_date > request.baseline_date
                if request.baseline_date is not None
                else current_date >= request.requested_at
            ):
                request.status = "updated"
            elif now >= request.deadline:
                request.status = "timeout"

    def _update_explorer_states(self, locations: dict[str, dict[str, Any]]) -> None:
        """Clear command overrides once location data reflects that state."""
        for device_id, active in list(self._explorer_overrides.items()):
            mode = locations.get(device_id, {}).get("trackingMode")
            if (active and mode == "EXPLORER") or (
                not active and mode in ("NORMAL", "SCHOOLWAY")
            ):
                self._explorer_overrides.pop(device_id)


def supports_chat_text(device: dict[str, Any]) -> bool:
    """Return whether text chat is enabled and supported by a device."""
    settings = device.get("settings")
    config = device.get("config")
    return (
        (not isinstance(settings, dict) or settings.get("isChatEnabled") is not False)
        and isinstance(config, dict)
        and config.get("hasTextChat") is True
    )


def supports_chat_incoming(device: dict[str, Any]) -> bool:
    """Return whether a device can send supported chat message types."""
    settings = device.get("settings")
    config = device.get("config")
    return (
        (not isinstance(settings, dict) or settings.get("isChatEnabled") is not False)
        and isinstance(config, dict)
        and (config.get("hasEmojis") is True or config.get("hasVoiceChat") is True)
    )


def supports_chat_voice(device: dict[str, Any]) -> bool:
    """Return whether voice chat is enabled and supported by a device."""
    settings = device.get("settings")
    config = device.get("config")
    return (
        (not isinstance(settings, dict) or settings.get("isChatEnabled") is not False)
        and isinstance(config, dict)
        and config.get("hasVoiceChat") is True
    )


def supports_chat_emoji(device: dict[str, Any]) -> bool:
    """Return whether emoji chat is enabled and supported by a device."""
    settings = device.get("settings")
    config = device.get("config")
    return (
        (not isinstance(settings, dict) or settings.get("isChatEnabled") is not False)
        and isinstance(config, dict)
        and config.get("hasEmojis") is True
    )


def get_chat_max_length(device: dict[str, Any]) -> int | None:
    """Return a valid device-specific text message limit, if available."""
    config = device.get("config")
    if not isinstance(config, dict):
        return None
    value = config.get("maxChatMessageLength")
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def _parse_activity(record: dict[str, Any]) -> AnioActivity | None:
    """Validate an activity and retain only fields needed for display."""
    activity_id = record.get("id")
    activity_type = record.get("type")
    text = record.get("text")
    timestamp = record.get("createdAt")
    if not (
        isinstance(activity_id, str)
        and activity_id.strip()
        and isinstance(activity_type, str)
        and activity_type.strip()
        and isinstance(text, str)
        and isinstance(timestamp, str)
    ):
        _LOGGER.warning("Ignoring malformed Anio activity metadata")
        return None
    try:
        created_at = dt_util.parse_datetime(timestamp)
    except ValueError:
        created_at = None
    if created_at is None:
        _LOGGER.warning("Ignoring Anio activity with an invalid timestamp")
        return None
    geofence = record.get("geofence")
    zone = geofence.get("name") if isinstance(geofence, dict) else record.get("zone")
    return AnioActivity(
        activity_id=activity_id,
        activity_type=activity_type.strip().upper(),
        text=text,
        zone=zone.strip() if isinstance(zone, str) and zone.strip() else None,
        created_at=dt_util.as_utc(created_at),
    )


def _parse_chat_message(record: dict[str, Any]) -> AnioChatMessage | None:
    """Validate and normalize one chat record returned by the API."""
    message_id = record.get("id")
    message_type = record.get("type")
    sender = record.get("sender")
    if not all(
        isinstance(value, str) and value for value in (message_id, message_type, sender)
    ):
        _LOGGER.warning("Ignoring malformed Anio chat message metadata")
        return None

    raw_text = record.get("text")
    raw_created_at = record.get("createdAt")
    created_at = (
        dt_util.parse_datetime(raw_created_at)
        if isinstance(raw_created_at, str)
        else None
    )
    if created_at is not None:
        created_at = dt_util.as_utc(created_at)

    return AnioChatMessage(
        message_id=message_id,
        message_type=message_type.strip().upper(),
        sender=sender.strip().upper(),
        text=raw_text if isinstance(raw_text, str) else None,
        created_at=created_at,
    )


def _chat_event_data(device_id: str, message: AnioChatMessage) -> dict[str, Any]:
    """Build the public event payload for a newly received watch message."""
    data: dict[str, Any] = {
        "device_id": device_id,
        "message_id": message.message_id,
        "message_type": message.message_type.lower(),
        "sender": message.sender.lower(),
        "timestamp": message.created_at.isoformat() if message.created_at else None,
    }
    if message.message_type == "EMOJI" and message.text is not None:
        data["message"] = message.text
    if message.message_type == "VOICE":
        data["audio_url"] = get_chat_audio_url(device_id, message.message_id)
    return data


def get_chat_audio_url(device_id: str, message_id: str) -> str:
    """Build the authenticated Home Assistant URL for a voice message."""
    return f"/api/anio/voice/{quote(device_id, safe='')}/{quote(message_id, safe='')}"


def _read_interval(value: Any) -> int:
    """Return a valid configured polling interval or the safe default."""
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 60 <= value <= 1800
        and value % 60 == 0
    ):
        return value
    return DEFAULT_SCAN_INTERVAL


def get_location_timestamp(
    location: dict[str, Any] | None, key: str
) -> datetime | None:
    """Return an API timestamp normalized to UTC."""
    if location is None:
        return None
    value = location.get(key)
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    return dt_util.as_utc(parsed) if parsed is not None else None


def get_poll_interval_seconds(
    locations: dict[str, dict[str, Any]],
    mode_intervals: dict[str, int],
    device_ids: set[str] | None = None,
    explorer_overrides: dict[str, bool] | None = None,
) -> int:
    """Choose the shortest configured interval, falling back for unknown modes."""
    intervals: list[int] = []
    watched_device_ids = device_ids if device_ids is not None else set(locations)
    for device_id in watched_device_ids:
        location = locations.get(device_id, {})
        if explorer_overrides is not None and device_id in explorer_overrides:
            mode = "EXPLORER" if explorer_overrides[device_id] else None
        else:
            mode = location.get("trackingMode")
        if not isinstance(mode, str) or not mode:
            _LOGGER.debug(
                "No Anio tracking mode for watch %s; using the fallback polling "
                "interval",
                device_id,
            )
            intervals.append(DEFAULT_SCAN_INTERVAL)
            continue
        if mode not in TRACKING_MODES:
            _LOGGER.warning(
                "Unknown Anio tracking mode for watch %s; using the fallback "
                "polling interval",
                device_id,
            )
            intervals.append(DEFAULT_SCAN_INTERVAL)
            continue
        intervals.append(mode_intervals.get(mode, DEFAULT_SCAN_INTERVAL))

    return min(intervals) if intervals else DEFAULT_SCAN_INTERVAL


def map_locations_to_devices(
    locations: list[dict[str, Any]], device_ids: set[str]
) -> dict[str, dict[str, Any]]:
    """Map location records by their explicit deviceId field."""
    locations_by_device: dict[str, dict[str, Any]] = {}
    for location in locations:
        device_id = location.get("deviceId")
        if not isinstance(device_id, str) or not device_id.strip():
            _LOGGER.warning("Ignoring Anio location record without a deviceId")
            continue

        device_id = device_id.strip()
        if device_id not in device_ids:
            _LOGGER.debug("Ignoring Anio location for an unregistered watch")
            continue
        if device_id in locations_by_device:
            _LOGGER.warning("Multiple Anio location records returned for one watch")
        locations_by_device[device_id] = location

    return locations_by_device
