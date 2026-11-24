"""Tests for Anio location mapping and entity value validation."""

import asyncio
import json
import logging
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest
from homeassistant.components.device_tracker import SourceType
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import async_handle_entity_calls
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.file import WriteError

from custom_components.anio.api import (
    AnioApiError,
    AnioConnectionError,
    AnioRateLimitError,
)
from custom_components.anio.binary_sensor import AnioLocatingEnabledBinarySensor
from custom_components.anio.const import CONF_ACTIVITY_INTERVAL
from custom_components.anio.coordinator import (
    CHAT_INITIAL_SINCE,
    AnioChatMessage,
    AnioCoordinator,
    LocationRequest,
    RadarSession,
    get_location_timestamp,
    get_poll_interval_seconds,
    map_locations_to_devices,
)
from custom_components.anio.device_tracker import AnioTracker
from custom_components.anio.entity import get_battery_level, get_valid_position
from custom_components.anio.notify import AnioChatNotifyEntity
from custom_components.anio.number import (
    AnioRadarDurationNumber,
    AnioRadarIntervalNumber,
)
from custom_components.anio.sensor import (
    AnioActivitySensor,
    AnioBatterySensor,
    AnioGpsAccuracySensor,
    AnioLastChatMessageSensor,
    AnioLocationRequestStatusSensor,
    AnioLocationTimestampSensor,
    AnioPositionSourceSensor,
    AnioRadarRemainingSensor,
    AnioRawLocationNumberSensor,
    AnioSignalStrengthSensor,
    AnioTrackingModeSensor,
)
from custom_components.anio.switch import (
    AnioBellProtectionSwitch,
    AnioExplorerSwitch,
    AnioRadarSwitch,
)
from custom_components.anio.text import AnioChatTextEntity
from custom_components.anio.voice import (
    MAX_VOICE_UPLOAD_BYTES,
    AnioVoiceFormatNotConfigured,
    AnioVoiceProxyView,
    AnioVoiceUploadView,
    async_convert_voice_audio,
)


def test_locations_are_mapped_by_device_id() -> None:
    """Location records are associated using their explicit watch ID."""
    watch_one = {"deviceId": "watch-1", "position": [52.1, 13.2]}
    watch_two = {"deviceId": "watch-2", "position": [48.1, 11.5]}

    assert map_locations_to_devices([watch_two, watch_one], {"watch-1", "watch-2"}) == {
        "watch-1": watch_one,
        "watch-2": watch_two,
    }


def test_locations_without_a_known_device_id_are_ignored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unmappable and unknown records are not assigned to a single watch."""
    caplog.set_level(logging.WARNING)

    result = map_locations_to_devices(
        [
            {"position": [52.1, 13.2]},
            {"deviceId": "unknown-watch", "position": [48.1, 11.5]},
        ],
        {"watch-1"},
    )

    assert result == {}
    assert "without a deviceId" in caplog.text


def test_poll_interval_uses_shortest_interval_for_watch_modes() -> None:
    """A shared location endpoint polls at the shortest active mode interval."""
    assert (
        get_poll_interval_seconds(
            {
                "watch-1": {"trackingMode": "NORMAL"},
                "watch-2": {"trackingMode": "EXPLORER"},
            },
            {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120},
        )
        == 120
    )


@pytest.mark.asyncio
async def test_coordinator_update_applies_mode_interval() -> None:
    """A location refresh maps watch data and applies the configured interval."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.api = Mock(
        async_get_last_locations=AsyncMock(
            return_value=[{"deviceId": "watch-1", "trackingMode": "EXPLORER"}]
        )
    )
    coordinator.device_ids = {"watch-1"}
    coordinator.mode_intervals = {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120}
    coordinator._location_requests = {}
    coordinator._explorer_overrides = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator._schedule_chat_poll = Mock()
    coordinator.update_interval = timedelta(seconds=300)

    locations = await coordinator._async_update_data()

    assert locations["watch-1"]["trackingMode"] == "EXPLORER"
    assert coordinator.update_interval == timedelta(seconds=120)


@pytest.mark.asyncio
async def test_chat_poll_deduplicates_and_fires_for_new_incoming() -> None:
    """Only newly observed watch messages emit the chat event."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.chat_device_ids = {"watch-1"}
    coordinator._chat_since = {"watch-1": CHAT_INITIAL_SINCE}
    coordinator._chat_initialized = set()
    coordinator._chat_available = {}
    coordinator._last_chat_messages = {}
    coordinator._chat_history = {}
    coordinator._chat_message_id_sets = {}
    coordinator._chat_store = SimpleNamespace(async_save=AsyncMock())
    coordinator._api_lock = asyncio.Lock()
    coordinator._chat_lock = asyncio.Lock()
    coordinator.hass = SimpleNamespace(bus=Mock())
    coordinator.api = Mock(
        async_get_chat_messages=AsyncMock(
            side_effect=[
                [
                    {
                        "id": "message-1",
                        "type": "EMOJI",
                        "sender": "DEVICE",
                        "text": "E02",
                        "createdAt": "2026-01-02T03:04:05Z",
                    },
                    {
                        "id": "message-app",
                        "type": "TEXT",
                        "sender": "APP",
                        "text": "hello",
                    },
                ],
                [
                    {
                        "id": "message-1",
                        "type": "EMOJI",
                        "sender": "DEVICE",
                        "text": "E02",
                        "createdAt": "2026-01-02T03:04:05Z",
                    },
                    {
                        "id": "message-3",
                        "type": "EMOJI",
                        "sender": "DEVICE",
                        "text": "E03",
                        "createdAt": "2026-01-02T03:05:05Z",
                    },
                    {
                        "id": "message-2",
                        "type": "VOICE",
                        "sender": "DEVICE",
                        "createdAt": "2026-01-02T03:03:05Z",
                    },
                ],
            ]
        )
    )

    await coordinator._async_update_chat_messages()
    await coordinator._async_update_chat_messages()

    assert (
        coordinator.api.async_get_chat_messages.await_args_list[0].kwargs["since"]
        == CHAT_INITIAL_SINCE
    )
    events = [call.args for call in coordinator.hass.bus.async_fire.call_args_list]
    assert [event[0] for event in events] == [
        "anio_chat_message_received",
        "anio_chat_message_received",
    ]
    event_data = {event[1]["message_id"]: event[1] for event in events}
    assert event_data["message-2"]["message_type"] == "voice"
    assert "message" not in event_data["message-2"]
    assert event_data["message-3"]["message"] == "E03"
    assert coordinator.last_chat_message("watch-1").message_id == "message-3"
    assert [message.message_id for message in coordinator.chat_messages("watch-1")] == [
        "message-app",
        "message-2",
        "message-1",
        "message-3",
    ]
    assert coordinator.chat_available("watch-1")


@pytest.mark.asyncio
async def test_chat_history_restores_and_fetches_only_new_messages() -> None:
    """Persisted messages and cursor survive restarts and deduplicate overlap."""
    stored_since = dt_util.parse_datetime("2026-11-22T15:00:00+00:00")
    stored_message = {
        "id": "message-old",
        "type": "TEXT",
        "sender": "DEVICE",
        "text": "Frühere Nachricht",
        "createdAt": "2026-11-22T14:00:00Z",
    }
    new_message = {
        "id": "message-new",
        "type": "TEXT",
        "sender": "DEVICE",
        "text": "Neue Nachricht",
        "createdAt": "2026-11-22T15:10:00Z",
    }
    store = SimpleNamespace(
        async_load=AsyncMock(
            return_value={
                "devices": {
                    "watch-1": {
                        "since": stored_since.isoformat(),
                        "messages": [stored_message],
                    }
                }
            }
        ),
        async_save=AsyncMock(),
    )
    coordinator = object.__new__(AnioCoordinator)
    coordinator.chat_device_ids = {"watch-1"}
    coordinator._chat_since = {"watch-1": CHAT_INITIAL_SINCE}
    coordinator._chat_initialized = set()
    coordinator._chat_available = {}
    coordinator._last_chat_messages = {}
    coordinator._chat_history = {}
    coordinator._chat_message_id_sets = {}
    coordinator._chat_store = store
    coordinator._api_lock = asyncio.Lock()
    coordinator._chat_lock = asyncio.Lock()
    coordinator.hass = SimpleNamespace(bus=Mock())
    coordinator.api = Mock(
        async_get_chat_messages=AsyncMock(return_value=[stored_message, new_message])
    )
    coordinator.data = {}
    coordinator.async_update_listeners = Mock()

    await coordinator.async_load_chat_history()
    await coordinator.async_refresh_chat("watch-1")

    coordinator.api.async_get_chat_messages.assert_awaited_once_with(
        "watch-1", since=stored_since
    )
    assert [message.message_id for message in coordinator.chat_messages("watch-1")] == [
        "message-old",
        "message-new",
    ]
    assert coordinator._last_chat_messages["watch-1"].message_id == "message-new"
    coordinator.hass.bus.async_fire.assert_called_once()
    store.async_save.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()
    saved_data = store.async_save.await_args.args[0]["devices"]["watch-1"]
    assert [message["id"] for message in saved_data["messages"]] == [
        "message-old",
        "message-new",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("chat_available", [True, False])
async def test_chat_refresh_does_not_change_location_status_or_schedule(
    chat_available: bool,
) -> None:
    """Chat refreshes must not mark old location data successful or reset its timer."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.data = {"watch-1": {"position": [52.1, 13.2]}}
    coordinator.last_update_success = False
    coordinator._listeners = {1: (Mock(), None)}
    coordinator._async_unsub_refresh = Mock()
    coordinator._schedule_refresh = Mock()
    coordinator._debounced_refresh = Mock()
    coordinator.async_update_listeners = Mock()
    coordinator._async_update_chat_messages = AsyncMock()
    coordinator.chat_available = Mock(return_value=chat_available)
    coordinator.logger = Mock()
    coordinator.name = "test"

    if chat_available:
        await coordinator.async_refresh_chat("watch-1")
    else:
        with pytest.raises(HomeAssistantError):
            await coordinator.async_refresh_chat("watch-1")

    assert coordinator.last_update_success is False
    assert coordinator.data == {"watch-1": {"position": [52.1, 13.2]}}
    coordinator._async_unsub_refresh.assert_not_called()
    coordinator._schedule_refresh.assert_not_called()
    coordinator._debounced_refresh.async_cancel.assert_not_called()
    coordinator.async_update_listeners.assert_called_once()


def test_command_notification_does_not_change_location_status_or_schedule() -> None:
    """Status notifications must not reset location polling or its error state."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.data = {"watch-1": {"position": [52.1, 13.2]}}
    coordinator.last_update_success = False
    coordinator._listeners = {1: (Mock(), None)}
    coordinator._async_unsub_refresh = Mock()
    coordinator._schedule_refresh = Mock()
    coordinator._debounced_refresh = Mock()
    coordinator.async_update_listeners = Mock()
    coordinator.logger = Mock()
    coordinator.name = "test"

    coordinator._notify_entities()

    assert coordinator.last_update_success is False
    coordinator._async_unsub_refresh.assert_not_called()
    coordinator._schedule_refresh.assert_not_called()
    coordinator._debounced_refresh.async_cancel.assert_not_called()
    coordinator.async_update_listeners.assert_called_once()


def test_chat_sensor_available_after_location_failure() -> None:
    """Chat availability depends on the chat poll, not the location poll."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.last_update_success = False
    coordinator._chat_available = {"watch-1": True}
    sensor = AnioLastChatMessageSensor(coordinator, {"id": "watch-1"})

    assert sensor.available

    coordinator._chat_available["watch-1"] = False
    assert not sensor.available


@pytest.mark.parametrize("entity_type", [AnioChatTextEntity, AnioChatNotifyEntity])
def test_chat_sending_available_after_location_failure(
    entity_type: type[AnioChatTextEntity] | type[AnioChatNotifyEntity],
) -> None:
    """A location failure must not disable independent chat sending."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.last_update_success = False
    entity = entity_type(coordinator, {"id": "watch-1"})

    assert entity.available


@pytest.mark.asyncio
async def test_coordinator_uses_ha_as_chat_sender() -> None:
    """Outgoing chat requests use the approved static sender name."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.api = Mock(
        async_send_chat_text=AsyncMock(),
        async_send_chat_emoji=AsyncMock(),
    )
    coordinator._api_lock = asyncio.Lock()
    coordinator.async_refresh_chat = AsyncMock()

    await coordinator.async_send_chat_text("watch-1", "Hallo")
    await coordinator.async_send_chat_emoji("watch-1", "E02")

    coordinator.api.async_send_chat_text.assert_awaited_once_with(
        "watch-1", username="HA", text="Hallo"
    )
    coordinator.api.async_send_chat_emoji.assert_awaited_once_with(
        "watch-1", username="HA", emoji_code="E02"
    )
    assert coordinator.async_refresh_chat.await_args_list == [
        call("watch-1"),
        call("watch-1"),
    ]


@pytest.mark.asyncio
async def test_chat_poll_error_does_not_fail_location_refresh() -> None:
    """A chat endpoint error is isolated from successful location updates."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.api = Mock(
        async_get_last_locations=AsyncMock(return_value=[]),
        async_get_chat_messages=AsyncMock(side_effect=AnioApiError("chat unavailable")),
    )
    coordinator.device_ids = {"watch-1"}
    coordinator.chat_device_ids = {"watch-1"}
    coordinator._chat_since = {"watch-1": dt_util.utcnow()}
    coordinator._chat_initialized = set()
    coordinator._chat_available = {}
    coordinator._last_chat_messages = {}
    coordinator._chat_message_id_sets = {}
    coordinator.mode_intervals = {"NORMAL": 300, "SCHOOLWAY": 300, "EXPLORER": 60}
    coordinator._location_requests = {}
    coordinator._explorer_overrides = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator._chat_lock = asyncio.Lock()
    coordinator._chat_poll_task = None
    coordinator.hass = SimpleNamespace()
    coordinator.config_entry = SimpleNamespace(
        async_create_background_task=lambda hass, coro, **kwargs: asyncio.create_task(
            coro
        )
    )
    coordinator.async_update_listeners = Mock()
    coordinator.update_interval = timedelta(seconds=300)

    locations = await coordinator._async_update_data()
    await coordinator._chat_poll_task

    assert locations == {}
    assert not coordinator.chat_available("watch-1")
    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_location_refresh_does_not_wait_for_chat_poll() -> None:
    """Location results are returned while a separate chat poll is still running."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.api = Mock(
        async_get_last_locations=AsyncMock(
            return_value=[{"deviceId": "watch-1", "trackingMode": "NORMAL"}]
        )
    )
    coordinator.device_ids = {"watch-1"}
    coordinator.chat_device_ids = {"watch-1"}
    coordinator.mode_intervals = {"NORMAL": 300, "SCHOOLWAY": 300, "EXPLORER": 60}
    coordinator._location_requests = {}
    coordinator._explorer_overrides = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator._chat_poll_task = None
    coordinator.update_interval = timedelta(seconds=300)
    coordinator.hass = SimpleNamespace()
    coordinator.config_entry = SimpleNamespace(
        async_create_background_task=Mock(
            side_effect=lambda hass, coro, **kwargs: asyncio.create_task(coro)
        )
    )
    coordinator.async_update_listeners = Mock()
    started = asyncio.Event()
    release = asyncio.Event()

    async def delayed_chat() -> None:
        started.set()
        await release.wait()

    coordinator._async_update_chat_messages = AsyncMock(side_effect=delayed_chat)
    try:
        locations = await asyncio.wait_for(coordinator._async_update_data(), timeout=1)
        await asyncio.wait_for(started.wait(), timeout=1)
        assert locations["watch-1"]["trackingMode"] == "NORMAL"
        assert not coordinator._chat_poll_task.done()
        coordinator._schedule_chat_poll()
        coordinator.config_entry.async_create_background_task.assert_called_once()
    finally:
        release.set()
        if coordinator._chat_poll_task is not None:
            await coordinator._chat_poll_task

    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_background_chat_storage_failure_does_not_change_location_status(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Chat storage errors are logged and surfaced without changing location status."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.chat_device_ids = {"watch-1"}
    coordinator._chat_available = {"watch-1": True}
    coordinator.last_update_success = True
    coordinator._async_update_chat_messages = AsyncMock(side_effect=OSError("disk"))
    coordinator.async_update_listeners = Mock()

    await coordinator._async_run_chat_poll()

    assert coordinator.last_update_success
    assert not coordinator.chat_available("watch-1")
    assert "Anio chat polling failed (OSError)" in caplog.text
    coordinator.async_update_listeners.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_chat_refreshes_serialize_fetch_and_save() -> None:
    """A card refresh cannot overtake the background poll's history write."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.chat_device_ids = {"watch-1"}
    coordinator._chat_since = {"watch-1": CHAT_INITIAL_SINCE}
    coordinator._chat_initialized = {"watch-1"}
    coordinator._chat_available = {}
    coordinator._last_chat_messages = {}
    coordinator._chat_history = {}
    coordinator._chat_message_id_sets = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator._chat_lock = asyncio.Lock()
    coordinator.hass = SimpleNamespace(bus=Mock())
    coordinator.async_update_listeners = Mock()
    coordinator.api = Mock(
        async_get_chat_messages=AsyncMock(
            return_value=[
                {
                    "id": "message-1",
                    "type": "TEXT",
                    "sender": "DEVICE",
                    "text": "Hello",
                    "createdAt": "2026-11-22T15:10:00Z",
                }
            ]
        )
    )
    save_started = asyncio.Event()
    release_save = asyncio.Event()

    async def save_history() -> None:
        save_started.set()
        await release_save.wait()

    coordinator._async_save_chat_history = AsyncMock(side_effect=save_history)
    first = asyncio.create_task(coordinator._async_update_chat_messages())
    second = None
    try:
        await asyncio.wait_for(save_started.wait(), timeout=1)
        second = asyncio.create_task(coordinator.async_refresh_chat("watch-1"))
        await asyncio.sleep(0)
        coordinator.api.async_get_chat_messages.assert_awaited_once()
    finally:
        release_save.set()
        await first
        if second is not None:
            await second

    assert coordinator.api.async_get_chat_messages.await_count == 2
    assert len(coordinator.chat_messages("watch-1")) == 1
    coordinator.hass.bus.async_fire.assert_called_once()


def activity_coordinator(store: Any, records: list[dict[str, Any]]) -> AnioCoordinator:
    """Create a coordinator with activity dependencies for focused tests."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.device_ids = {"watch-1", "watch-2"}
    coordinator._activity_history = {}
    coordinator._activity_available = False
    coordinator._activity_dirty = False
    coordinator._activity_refresh_task = None
    coordinator._activity_last_started = None
    coordinator._activity_store = store
    coordinator._api_lock = asyncio.Lock()
    coordinator.api = Mock(async_get_activities=AsyncMock(return_value=records))
    coordinator.hass = SimpleNamespace(
        bus=Mock(), async_create_task=asyncio.create_task
    )
    coordinator.async_update_listeners = Mock()
    return coordinator


@pytest.mark.asyncio
async def test_activity_history_sorts_deduplicates_and_survives_restart(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retain minimized records per watch and reconstruct them on restart."""
    left = {
        "id": "left",
        "deviceId": "watch-1",
        "type": "GEOFENCE_LEFT",
        "text": "Left",
        "createdAt": "2026-01-02T08:15:00.600Z",
        "geofence": {"name": "Home", "location": [1, 2]},
    }
    entered = {
        **left,
        "id": "entered",
        "type": "GEOFENCE_ENTERED",
        "createdAt": "2026-01-02T08:14:00.600Z",
        "geofence": {"name": "School"},
    }
    unknown = {
        "id": "unknown",
        "deviceId": "watch-2",
        "type": "NEW_EVENT",
        "text": "Some event",
        "createdAt": "2026-01-02T08:16:00Z",
    }
    store = SimpleNamespace(async_load=AsyncMock(), async_save=AsyncMock())
    store.async_load.side_effect = lambda: store.async_save.await_args.args[0]
    coordinator = activity_coordinator(
        store,
        [
            left,
            entered,
            unknown,
            left,
            {**unknown, "deviceId": "other"},
            {**unknown, "id": "bad", "createdAt": "invalid"},
        ],
    )
    await coordinator._async_update_activities()
    assert coordinator.activity_available()
    assert [a.activity_id for a in coordinator.activities("watch-1")] == [
        "entered",
        "left",
    ]
    assert coordinator.activities("watch-1")[1].display_time.isoformat() == (
        "2026-01-02T08:14:01+00:00"
    )
    assert [a.activity_type for a in coordinator.activities("watch-2")] == ["NEW_EVENT"]
    assert "unknown device" in caplog.text
    assert "invalid timestamp" in caplog.text
    coordinator.hass.bus.async_fire.assert_not_called()
    saved = store.async_save.await_args.args[0]
    assert "location" not in json.dumps(saved)
    assert saved["devices"]["watch-1"][0]["createdAt"].endswith("00.600000+00:00")

    store.async_load.side_effect = None
    store.async_load.return_value = saved
    store.async_save.reset_mock()
    restored = activity_coordinator(store, [left, unknown])
    await restored.async_load_activity_history()
    await restored._async_update_activities()
    assert [a.activity_id for a in restored.activities("watch-1")] == [
        "entered",
        "left",
    ]
    assert restored.activities("watch-2")[0].text == "Some event"
    store.async_save.assert_not_awaited()

    restored.last_update_success = True
    sensor = AnioActivitySensor(restored, {"id": "watch-1"})
    assert sensor.native_value == "geofence_entered"
    assert sensor.extra_state_attributes["activities"][1]["timestamp"].endswith(
        "00.600000+00:00"
    )
    assert "activities" in sensor._unrecorded_attributes


@pytest.mark.asyncio
async def test_activity_errors_do_not_block_location_and_failed_save_is_retried(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Keep location updates working and retry unsaved activities on the next poll."""
    store = SimpleNamespace(
        async_load=AsyncMock(), async_save=AsyncMock(side_effect=[OSError(), None])
    )
    store.async_load.side_effect = lambda: store.async_save.await_args.args[0]
    record = {
        "id": "a",
        "deviceId": "watch-1",
        "type": "LOW_BATTERY",
        "text": "Battery low",
        "createdAt": "2026-01-02T08:15:00Z",
    }
    coordinator = activity_coordinator(store, [record])
    coordinator.api.async_get_last_locations = AsyncMock(return_value=[])
    coordinator._async_update_chat_messages = AsyncMock()
    coordinator.mode_intervals = {"NORMAL": 300, "SCHOOLWAY": 300, "EXPLORER": 60}
    coordinator._location_requests = {}
    coordinator._explorer_overrides = {}
    coordinator.update_interval = timedelta(seconds=300)
    coordinator._schedule_chat_poll = Mock()
    assert await coordinator._async_update_data() == {}
    coordinator.api.async_get_activities.assert_not_awaited()
    await coordinator._async_update_activities()
    assert not coordinator.activity_available()
    assert "Could not save Anio activity history" in caplog.text
    await coordinator._async_update_activities()
    assert coordinator.activity_available()
    assert store.async_save.await_count == 2
    coordinator.api.async_get_activities.side_effect = AnioApiError("offline")
    await coordinator._async_update_activities()
    assert await coordinator._async_update_data() == {}
    assert not coordinator.activity_available()
    assert len(coordinator.activities("watch-1")) == 1
    assert "activity polling failed" in caplog.text


@pytest.mark.asyncio
async def test_activity_refresh_coalesces_and_throttles_automatic_openings() -> None:
    """Share in-flight refreshes and allow manual retries during the cooldown."""
    store = SimpleNamespace(async_load=AsyncMock(), async_save=AsyncMock())
    coordinator = activity_coordinator(store, [])
    started = asyncio.Event()
    release = asyncio.Event()

    async def fetch() -> list:
        started.set()
        await release.wait()
        return []

    coordinator.api.async_get_activities.side_effect = fetch
    first = asyncio.create_task(coordinator.async_refresh_activities(force=False))
    await started.wait()
    second = asyncio.create_task(coordinator.async_refresh_activities(force=True))
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)
    coordinator.api.async_get_activities.assert_awaited_once()
    coordinator.async_update_listeners.assert_called_once()
    await coordinator.async_refresh_activities(force=False)
    coordinator.api.async_get_activities.assert_awaited_once()
    await coordinator.async_refresh_activities(force=True)
    assert coordinator.api.async_get_activities.await_count == 2
    assert coordinator.async_update_listeners.call_count == 2
    coordinator._activity_last_started -= 31
    await coordinator.async_refresh_activities(force=False)
    assert coordinator.api.async_get_activities.await_count == 3


@pytest.mark.asyncio
async def test_activity_refresh_failure_notifies_and_reports_error() -> None:
    """An activity failure is visible without marking location data failed."""
    store = SimpleNamespace(async_load=AsyncMock(), async_save=AsyncMock())
    coordinator = activity_coordinator(store, [])
    coordinator.api.async_get_activities.side_effect = AnioApiError("offline")
    coordinator.last_update_success = False
    with pytest.raises(HomeAssistantError) as err:
        await coordinator.async_refresh_activities()
    assert err.value.translation_key == "activity_refresh_failed"
    coordinator.async_update_listeners.assert_called_once()
    sensor = AnioActivitySensor(coordinator, {"id": "watch-1"})
    assert sensor.available
    assert sensor.extra_state_attributes["update_available"] is False
    with pytest.raises(HomeAssistantError):
        await coordinator.async_refresh_activities(force=False)
    coordinator.api.async_get_activities.assert_awaited_once()
    coordinator.api.async_get_activities.side_effect = None
    await coordinator.async_refresh_activities(force=True)
    assert coordinator.api.async_get_activities.await_count == 2
    assert coordinator.activity_available()


@pytest.mark.parametrize(
    ("options", "minutes"), [({}, 60), ({CONF_ACTIVITY_INTERVAL: 17}, 17)]
)
def test_activity_schedule_uses_configured_interval(
    options: dict[str, int], minutes: int
) -> None:
    """The account's independent timer uses the saved interval or its default."""
    entry = SimpleNamespace(entry_id="entry-1", options=options)
    with (
        patch(
            "custom_components.anio.coordinator.DataUpdateCoordinator.__init__",
            return_value=None,
        ),
        patch("custom_components.anio.coordinator.Store"),
    ):
        coordinator = AnioCoordinator(Mock(), Mock(), entry, [])
    assert coordinator.activity_interval == timedelta(minutes=minutes)


@pytest.mark.asyncio
async def test_scheduled_activities_run_when_location_poll_fails() -> None:
    """A failed location refresh does not prevent an independent activity poll."""
    store = SimpleNamespace(async_load=AsyncMock(), async_save=AsyncMock())
    coordinator = activity_coordinator(store, [])
    coordinator.api.async_get_last_locations = AsyncMock(
        side_effect=AnioConnectionError("offline")
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
    await coordinator.async_scheduled_activity_refresh()
    coordinator.api.async_get_activities.assert_awaited_once()
    assert coordinator.activity_available()


@pytest.mark.asyncio
async def test_activity_store_detects_swallowed_write_error_and_restores(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Verify HA Store's logged write failures are detected and retried."""
    hass = HomeAssistant(str(tmp_path))
    store = Store(hass, 1, "anio_test_activity", private=True)
    record = {
        "id": "a",
        "deviceId": "watch-1",
        "type": "LOW_BATTERY",
        "text": "Battery low",
        "createdAt": "2026-01-02T08:15:00Z",
    }
    coordinator = activity_coordinator(store, [record])
    with patch(
        "homeassistant.helpers.storage.write_utf8_file", side_effect=WriteError("disk")
    ):
        await coordinator._async_update_activities()
    assert not coordinator.activity_available()
    assert "Could not verify saved Anio activity history" in caplog.text
    await coordinator._async_update_activities()
    assert coordinator.activity_available()
    fresh_store = Store(hass, 1, "anio_test_activity", private=True)
    restored = activity_coordinator(fresh_store, [])
    await restored.async_load_activity_history()
    assert restored.activities("watch-1")[0].activity_id == "a"
    hass.import_executor.shutdown(wait=True)


@pytest.mark.asyncio
async def test_chat_notify_validates_device_message_limit() -> None:
    """Outgoing messages over the device limit are rejected without truncation."""
    entity = object.__new__(AnioChatNotifyEntity)
    entity._device_id = "watch-1"
    entity._device = {"config": {"maxChatMessageLength": 4}}
    entity.coordinator = SimpleNamespace(async_send_chat_text=AsyncMock())
    entity.hass = SimpleNamespace(auth=SimpleNamespace(async_get_user=AsyncMock()))

    with pytest.raises(HomeAssistantError) as err:
        await entity.async_send_message("Hallo")
    assert err.value.translation_key == "message_too_long"
    assert err.value.translation_placeholders == {"max_length": "4"}

    await entity.async_send_message("Hi")
    entity.coordinator.async_send_chat_text.assert_awaited_once_with(
        "watch-1", "Hi", username="HA"
    )


@pytest.mark.asyncio
async def test_chat_text_entity_sends_and_clears_after_success() -> None:
    """The native text entity keeps its draft only until a successful send."""
    coordinator = Mock()
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.async_send_chat_text = AsyncMock()
    entity = AnioChatTextEntity(
        coordinator,
        {
            "id": "watch-1",
            "settings": {},
            "config": {"hasTextChat": True, "maxChatMessageLength": 20},
        },
    )
    entity.async_write_ha_state = Mock()
    entity.hass = SimpleNamespace(auth=SimpleNamespace(async_get_user=AsyncMock()))

    await entity.async_set_value("Hallo")

    coordinator.async_send_chat_text.assert_awaited_once_with(
        "watch-1", "Hallo", username="HA"
    )
    assert entity.native_value == ""
    entity.async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_chat_text_entity_rejects_overlong_messages() -> None:
    """The native text entity enforces the watch limit without truncation."""
    coordinator = Mock()
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.async_send_chat_text = AsyncMock()
    entity = AnioChatTextEntity(
        coordinator,
        {
            "id": "watch-1",
            "settings": {},
            "config": {"hasTextChat": True, "maxChatMessageLength": 4},
        },
    )
    entity.async_write_ha_state = Mock()

    with pytest.raises(HomeAssistantError) as err:
        await entity.async_set_value("Hallo")
    assert err.value.translation_key == "message_too_long"
    assert err.value.translation_placeholders == {"max_length": "4"}

    coordinator.async_send_chat_text.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_type", ["text", "notify"])
@pytest.mark.parametrize(
    ("user_id", "user", "expected"),
    [
        ("user-1", SimpleNamespace(name="Alice Müller"), "Alice Müller"),
        (None, None, "HA"),
        ("user-1", None, "HA"),
        ("user-1", SimpleNamespace(name=""), "HA"),
        ("user-1", SimpleNamespace(name="   "), "HA"),
    ],
)
async def test_chat_text_sender_uses_entity_context(
    entity_type: str, user_id: str | None, user: object, expected: str
) -> None:
    """Both entity services pass the resolved sender through to the API."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.api = Mock(async_send_chat_text=AsyncMock())
    coordinator._api_lock = asyncio.Lock()
    coordinator.async_refresh_chat = AsyncMock()
    device = {"id": "watch-1", "settings": {}, "config": {"hasTextChat": True}}
    if entity_type == "text":
        entity = AnioChatTextEntity(coordinator, device)
        entity.async_write_ha_state = Mock()
        method, data = "async_set_value", {"value": "Hello"}
    else:
        entity = AnioChatNotifyEntity(coordinator, device)
        method, data = "async_send_message", {"message": "Hello"}
    lookup = AsyncMock(return_value=user)
    entity.hass = SimpleNamespace(auth=SimpleNamespace(async_get_user=lookup))
    entity.entity_id = f"{entity_type}.watch_chat"

    await async_handle_entity_calls(
        method, [(entity, data)], context=Context(user_id=user_id)
    )

    coordinator.api.async_send_chat_text.assert_awaited_once_with(
        "watch-1", username=expected, text="Hello"
    )
    if user_id:
        lookup.assert_awaited_once_with(user_id)
    else:
        lookup.assert_not_awaited()
    coordinator.async_refresh_chat.assert_awaited_once_with("watch-1")


@pytest.mark.asyncio
async def test_chat_sender_lookup_error_is_not_silenced() -> None:
    """Unexpected authentication failures do not silently change the sender."""
    coordinator = Mock(async_send_chat_text=AsyncMock())
    entity = AnioChatNotifyEntity(coordinator, {"id": "watch-1"})
    entity.hass = SimpleNamespace(
        auth=SimpleNamespace(async_get_user=AsyncMock(side_effect=RuntimeError("error")))
    )
    entity.async_set_context(Context(user_id="user-1"))

    with pytest.raises(RuntimeError, match="error"):
        await entity.async_send_message("Hello")

    coordinator.async_send_chat_text.assert_not_awaited()


def test_last_chat_sensor_exposes_a_safe_voice_proxy_and_history() -> None:
    """Voice URLs point only to HA and the sensor exposes a chronological list."""
    voice = AnioChatMessage(
        "message-voice",
        "VOICE",
        "DEVICE",
        "https://audio.example.invalid/voice?token=redacted",
        dt_util.parse_datetime("2026-01-02T03:04:05Z"),
    )
    text = AnioChatMessage(
        "message-text",
        "TEXT",
        "APP",
        "Hallo",
        dt_util.parse_datetime("2026-01-02T03:03:05Z"),
    )
    coordinator = Mock()
    coordinator.data = {"watch-1": {}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    coordinator.chat_available.return_value = True
    coordinator.last_chat_message.return_value = voice
    coordinator.chat_messages.return_value = [text, voice]
    sensor = AnioLastChatMessageSensor(
        coordinator, {"id": "watch-1", "settings": {}, "config": {}}
    )

    assert sensor.native_value == "voice"
    assert sensor.extra_state_attributes == {
        "message_id": "message-voice",
        "message_type": "voice",
        "sender": "device",
        "timestamp": "2026-01-02T03:04:05+00:00",
        "is_from_watch": True,
        "audio_url": "/api/anio/voice/watch-1/message-voice",
        "messages": [
            {
                "message_id": "message-text",
                "sender": "app",
                "timestamp": "2026-01-02T03:03:05+00:00",
                "message_type": "text",
                "message": "Hallo",
                "is_from_watch": False,
                "audio_url": None,
            },
            {
                "message_id": "message-voice",
                "sender": "device",
                "timestamp": "2026-01-02T03:04:05+00:00",
                "message_type": "voice",
                "message": None,
                "is_from_watch": True,
                "audio_url": "/api/anio/voice/watch-1/message-voice",
            },
        ],
    }


@pytest.mark.asyncio
async def test_voice_views_require_auth_and_do_not_guess_audio_protocol() -> None:
    """Authenticated voice routes return explicit stubs until traces exist."""
    voice_message = AnioChatMessage(
        "voice-1", "VOICE", "DEVICE", None, dt_util.utcnow()
    )
    coordinator = object.__new__(AnioCoordinator)
    coordinator.devices = [
        {"id": "watch-1", "settings": {}, "config": {"hasVoiceChat": True}}
    ]
    coordinator._chat_history = {"watch-1": [voice_message]}

    class UploadContent:
        async def iter_chunked(self, _chunk_size: int):
            yield b"audio"

    request = SimpleNamespace(
        app={"hass": SimpleNamespace(data={"anio": {"entry": coordinator}})},
        content_type="audio/webm",
        content_length=5,
        content=UploadContent(),
    )

    assert AnioVoiceProxyView.requires_auth
    assert AnioVoiceUploadView.requires_auth
    proxy_response = await AnioVoiceProxyView().get(request, "watch-1", "voice-1")
    upload_response = await AnioVoiceUploadView().post(request, "watch-1")
    missing_response = await AnioVoiceProxyView().get(
        request, "watch-1", "unknown-message"
    )
    oversized_request = SimpleNamespace(
        app=request.app,
        content_type="audio/webm",
        content_length=MAX_VOICE_UPLOAD_BYTES + 1,
        content=Mock(),
    )
    oversized_response = await AnioVoiceUploadView().post(oversized_request, "watch-1")

    assert proxy_response.status == 501
    assert upload_response.status == 501
    assert missing_response.status == 404
    assert oversized_response.status == 413
    assert json.loads(proxy_response.text)["code"] == "voice_source_not_verified"
    assert json.loads(upload_response.text)["code"] == "voice_format_not_configured"
    assert json.loads(missing_response.text)["code"] == "voice_message_not_found"
    assert json.loads(oversized_response.text)["code"] == "audio_too_large"
    with pytest.raises(AnioVoiceFormatNotConfigured):
        await async_convert_voice_audio(b"audio", "audio/webm")


def test_poll_interval_uses_fallback_for_unknown_mode(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown tracking values use the documented conservative fallback."""
    caplog.set_level(logging.WARNING)

    assert (
        get_poll_interval_seconds(
            {"watch-1": {"trackingMode": "UNEXPECTED"}},
            {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120},
        )
        == 300
    )
    assert "Unknown Anio tracking mode" in caplog.text


def test_poll_interval_uses_fallback_when_a_watch_has_no_location() -> None:
    """A missing watch record cannot inherit another watch's faster interval."""
    assert (
        get_poll_interval_seconds(
            {"watch-1": {"trackingMode": "NORMAL"}},
            {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120},
            {"watch-1", "watch-2"},
        )
        == 300
    )


@pytest.mark.parametrize(
    ("location_mode", "explorer_override", "expected_interval"),
    [
        ("NORMAL", True, 120),
        ("EXPLORER", False, 300),
    ],
)
def test_explorer_command_updates_polling_before_location_record(
    location_mode: str,
    explorer_override: bool,
    expected_interval: int,
) -> None:
    """A confirmed Explorer command overrides stale location-mode data."""
    assert (
        get_poll_interval_seconds(
            {"watch-1": {"trackingMode": location_mode}},
            {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120},
            {"watch-1"},
            {"watch-1": explorer_override},
        )
        == expected_interval
    )


@pytest.mark.asyncio
async def test_repeated_explorer_activation_keeps_confirmed_override() -> None:
    """A stale location mode cannot undo a confirmed Explorer state on retry."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.data = {"watch-1": {"trackingMode": "NORMAL"}}
    coordinator.device_ids = {"watch-1"}
    coordinator.mode_intervals = {"NORMAL": 600, "SCHOOLWAY": 300, "EXPLORER": 120}
    coordinator._explorer_overrides = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator.update_interval = timedelta(seconds=600)
    coordinator.api = Mock(async_set_explorer=AsyncMock(return_value={"active": True}))
    coordinator._notify_entities = Mock()
    coordinator._listeners = {1: (Mock(), None)}
    previous_timer_cancel = Mock()
    new_timer_cancel = Mock()
    loop = SimpleNamespace(
        time=Mock(return_value=100.0),
        call_at=Mock(return_value=SimpleNamespace(cancel=new_timer_cancel)),
    )
    coordinator.hass = SimpleNamespace(loop=loop)
    coordinator.config_entry = None
    coordinator._unsub_refresh = previous_timer_cancel
    coordinator._retry_after = None
    coordinator._microsecond = 0
    coordinator.name = "test"

    await coordinator.async_set_explorer("watch-1", activate=True)
    await coordinator.async_set_explorer("watch-1", activate=True)

    assert coordinator._explorer_overrides == {"watch-1": True}
    assert coordinator.update_interval == timedelta(seconds=120)
    previous_timer_cancel.assert_called_once()
    loop.call_at.assert_called_once()
    assert loop.call_at.call_args.args[0] == 220
    assert coordinator._unsub_refresh is new_timer_cancel


def test_location_request_completes_only_for_a_newer_fix() -> None:
    """A changed position timestamp, not an API response timestamp, completes it."""
    coordinator = object.__new__(AnioCoordinator)
    now = dt_util.utcnow()
    coordinator._location_requests = {
        "watch-1": LocationRequest(
            requested_at=now,
            baseline_date=dt_util.parse_datetime("2026-11-19T23:02:00.000Z"),
            deadline=now + timedelta(minutes=10),
        )
    }

    coordinator._update_location_requests(
        {
            "watch-1": {
                "date": "2026-11-19T23:02:00.000Z",
                "lastResponse": "2026-11-19T23:10:00.000Z",
            }
        }
    )
    assert coordinator.location_request_status("watch-1") == "requesting"

    coordinator._update_location_requests(
        {"watch-1": {"date": "2026-11-19T23:12:00.000Z"}}
    )
    assert coordinator.location_request_status("watch-1") == "updated"


def test_location_request_times_out_without_a_new_fix() -> None:
    """A changed last-response timestamp alone cannot prevent request timeout."""
    coordinator = object.__new__(AnioCoordinator)
    now = dt_util.utcnow()
    coordinator._location_requests = {
        "watch-1": LocationRequest(
            requested_at=now - timedelta(minutes=11),
            baseline_date=dt_util.parse_datetime("2026-11-19T23:02:00.000Z"),
            deadline=now - timedelta(seconds=1),
        )
    }

    coordinator._update_location_requests(
        {
            "watch-1": {
                "date": "2026-11-19T23:02:00.000Z",
                "lastResponse": "2026-11-19T23:10:00.000Z",
            }
        }
    )
    assert coordinator.location_request_status("watch-1") == "timeout"


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        ([52.1, 13.2], (52.1, 13.2)),
        ([91, 13.2], None),
        ([10**400, 13.2], None),
        ([52.1, float("nan")], None),
        (["52.1", 13.2], None),
        (None, None),
    ],
)
def test_position_validation(
    position: object, expected: tuple[float, float] | None
) -> None:
    """Only numeric, finite, in-range coordinates are accepted."""
    assert get_valid_position({"position": position}) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (78, 78),
        (0, 0),
        (100, 100),
        (-1, None),
        (101, None),
        (10**400, None),
        ("78", None),
        (None, None),
    ],
)
def test_battery_level_validation(value: object, expected: int | float | None) -> None:
    """Battery values must be numeric percentages in the API's valid range."""
    assert get_battery_level({"batteryLevel": value}) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-11-19T23:02:00.000Z", "2026-11-19T23:02:00+00:00"),
        ("not-a-timestamp", None),
        (None, None),
        (123, None),
    ],
)
def test_location_timestamp_validation(value: object, expected: str | None) -> None:
    """Only parseable API timestamp strings are exposed, normalized to UTC."""
    timestamp = get_location_timestamp({"date": value}, "date")
    assert (timestamp.isoformat() if timestamp else None) == expected


def test_tracker_and_battery_sensor_use_the_watch_record() -> None:
    """Entities expose mapped coordinates and battery values for their watch."""
    location = {
        "position": [52.1, 13.2],
        "batteryLevel": 78,
        "accuracy": 0,
        "speed": 0,
        "direction": 0,
    }
    coordinator = Mock()
    coordinator.data = {"watch-1": location}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    device = {"id": "watch-1", "settings": {"name": "Watch"}, "config": {}}

    tracker = AnioTracker(coordinator, device)
    battery = AnioBatterySensor(coordinator, device)
    accuracy = AnioGpsAccuracySensor(coordinator, device)
    tracking_mode = AnioTrackingModeSensor(coordinator, device)
    request_status = AnioLocationRequestStatusSensor(coordinator, device)
    explorer = AnioExplorerSwitch(coordinator, device)
    coordinator.tracking_mode.return_value = "EXPLORER"
    coordinator.location_request_status.return_value = "idle"
    coordinator.explorer_active.return_value = True

    assert (tracker.latitude, tracker.longitude) == (52.1, 13.2)
    assert tracker.source_type is SourceType.GPS
    assert tracker.entity_category is None
    assert tracker.location_accuracy == 0
    assert tracker.available
    assert tracker.extra_state_attributes is None
    assert accuracy.native_value == 0
    assert battery.native_value == 78
    assert tracking_mode.native_value == "explorer"
    assert request_status.native_value == "idle"
    assert request_status.entity_category is EntityCategory.DIAGNOSTIC
    assert request_status.icon == "mdi:map-clock-outline"
    assert explorer.is_on
    assert explorer.available


def test_diagnostic_entities_expose_location_and_device_settings() -> None:
    """Diagnostic entities expose telemetry without inferring unknown units."""
    location = {
        "date": "2026-11-19T23:02:00.000Z",
        "lastResponse": "2026-11-19T23:10:00.000Z",
        "positionDeterminedBy": "GPS",
        "signalStrength": 40,
        "accuracy": 8,
        "speed": 0,
        "direction": 0,
    }
    device = {
        "id": "watch-1",
        "settings": {"isLocatingActive": True},
        "config": {},
    }
    coordinator = Mock()
    coordinator.data = {"watch-1": location}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)

    last_location = AnioLocationTimestampSensor(
        coordinator, device, "date", "last_location"
    )
    last_response = AnioLocationTimestampSensor(
        coordinator, device, "lastResponse", "last_response"
    )
    source = AnioPositionSourceSensor(coordinator, device)
    strength = AnioSignalStrengthSensor(coordinator, device)
    accuracy = AnioGpsAccuracySensor(coordinator, device)
    speed = AnioRawLocationNumberSensor(coordinator, device, "speed", "mdi:speedometer")
    direction = AnioRawLocationNumberSensor(
        coordinator, device, "direction", "mdi:compass-outline"
    )
    locating_enabled = AnioLocatingEnabledBinarySensor(device)

    assert last_location.native_value == dt_util.parse_datetime(
        "2026-11-19T23:02:00.000Z"
    )
    assert last_response.native_value == dt_util.parse_datetime(
        "2026-11-19T23:10:00.000Z"
    )
    assert source.native_value == "GPS"
    assert source.icon == "mdi:satellite-variant"
    assert strength.native_value == 40
    assert strength.native_unit_of_measurement == "%"
    assert strength.icon == "mdi:signal-cellular-2"
    assert accuracy.native_value == 8
    assert accuracy.native_unit_of_measurement == UnitOfLength.METERS
    assert accuracy.device_class is SensorDeviceClass.DISTANCE
    assert accuracy.entity_category is EntityCategory.DIAGNOSTIC
    assert speed.native_value == 0
    assert direction.native_value == 0
    assert locating_enabled.is_on
    assert locating_enabled.available


@pytest.mark.parametrize(
    ("settings", "expected_available", "expected_on"),
    [
        ({"isLocatingActive": False}, True, False),
        ({}, False, False),
        ({"isLocatingActive": "true"}, False, False),
    ],
)
def test_locating_enabled_requires_a_boolean_setting(
    settings: dict[str, object], expected_available: bool, expected_on: bool
) -> None:
    """Missing or malformed settings do not appear as a valid enabled state."""
    coordinator = Mock()
    coordinator.data = {}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioLocatingEnabledBinarySensor(
        {"id": "watch-1", "settings": settings, "config": {}}
    )

    assert sensor.available is expected_available
    assert sensor.is_on is expected_on


@pytest.mark.parametrize(
    "value",
    [True, -1, 101, float("inf"), float("nan"), 10**400, "40"],
)
def test_signal_strength_rejects_non_numeric_or_unrepresentable_values(
    value: object,
) -> None:
    """Only finite values in the confirmed percentage range are exposed."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"signalStrength": value}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)

    sensor = AnioSignalStrengthSensor(
        coordinator,
        {"id": "watch-1", "settings": {}, "config": {}},
    )

    assert sensor.native_value is None


@pytest.mark.parametrize(
    ("value", "expected_icon"),
    [
        (0, "mdi:signal-cellular-1"),
        (100, "mdi:signal-cellular-3"),
    ],
)
def test_signal_strength_accepts_percentage_boundaries(
    value: int, expected_icon: str
) -> None:
    """Zero and one hundred map to the cellular signal icon endpoints."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"signalStrength": value}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioSignalStrengthSensor(
        coordinator,
        {"id": "watch-1", "settings": {}, "config": {}},
    )

    assert sensor.native_value == value
    assert sensor.icon == expected_icon


def test_position_source_icon_tracks_reported_method() -> None:
    """Known position sources have suitable icons; unknown values stay generic."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"positionDeterminedBy": "WIFI"}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioPositionSourceSensor(
        coordinator,
        {"id": "watch-1", "settings": {}, "config": {}},
    )

    assert sensor.icon == "mdi:wifi"
    coordinator.data["watch-1"]["positionDeterminedBy"] = "CELLULAR"
    assert sensor.icon == "mdi:map-marker"


@pytest.mark.parametrize(
    "value",
    [True, -1, float("inf"), float("nan"), 10**400, "8"],
)
def test_accuracy_sensor_rejects_malformed_values(value: object) -> None:
    """GPS accuracy only exposes valid non-negative finite numbers."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"accuracy": value}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)

    sensor = AnioGpsAccuracySensor(
        coordinator, {"id": "watch-1", "settings": {}, "config": {}}
    )

    assert sensor.native_value is None


def test_chat_history_is_unbounded_and_text_state_stays_within_255_characters() -> None:
    """The sensor retains the full conversation and caps its state value."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator._chat_history = {}
    timestamp = dt_util.utcnow()

    for index in range(12):
        coordinator._remember_chat_message(
            "watch-1",
            AnioChatMessage(
                f"message-{index}",
                "TEXT",
                "DEVICE",
                "x" * 300,
                timestamp + timedelta(seconds=index),
            ),
        )

    assert [message.message_id for message in coordinator.chat_messages("watch-1")] == [
        f"message-{index}" for index in range(12)
    ]
    coordinator._remember_chat_message(
        "watch-1",
        AnioChatMessage(
            "late-old-message",
            "TEXT",
            "DEVICE",
            "old",
            timestamp + timedelta(milliseconds=500),
        ),
    )
    assert [message.message_id for message in coordinator.chat_messages("watch-1")] == [
        "message-0",
        "late-old-message",
        *[f"message-{index}" for index in range(1, 12)],
    ]
    coordinator.last_chat_message = Mock(
        return_value=coordinator.chat_messages("watch-1")[-1]
    )
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioLastChatMessageSensor(
        coordinator, {"id": "watch-1", "settings": {}, "config": {}}
    )

    assert sensor.native_value == "x" * 255


def test_tracker_is_available_when_update_succeeds_but_position_is_invalid() -> None:
    """Missing coordinates do not imply that the coordinator is unavailable."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"position": [91, 13.2]}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)

    tracker = AnioTracker(coordinator, {"id": "watch-1", "settings": {}, "config": {}})

    assert tracker.latitude is None
    assert tracker.available
    assert tracker.state is None


def test_tracker_uses_api_accuracy_and_sensor_is_separate() -> None:
    """Trackers retain numeric accuracy while the sensor exposes the API value."""
    coordinator = Mock()
    coordinator.data = {"watch-1": {"position": [52.1, 13.2], "accuracy": 12}}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    device = {"id": "watch-1", "settings": {}, "config": {}}
    tracker = AnioTracker(coordinator, device)
    accuracy_sensor = AnioGpsAccuracySensor(coordinator, device)

    assert tracker.location_accuracy == 12
    assert tracker.extra_state_attributes is None
    assert accuracy_sensor.native_value == 12


@pytest.mark.parametrize("location", [{}, {"accuracy": None}])
def test_gps_accuracy_sensor_preserves_missing_values_as_none(
    location: dict[str, object],
) -> None:
    """Missing and null API accuracy values remain unknown."""
    coordinator = Mock()
    coordinator.data = {"watch-1": location}
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioGpsAccuracySensor(
        coordinator, {"id": "watch-1", "settings": {}, "config": {}}
    )

    assert sensor.native_value is None


def test_tracking_mode_sensor_normalizes_enum_values() -> None:
    """API mode names map to the translated enum options."""
    coordinator = Mock()
    coordinator.tracking_mode.return_value = "NORMAL"
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    sensor = AnioTrackingModeSensor(
        coordinator, {"id": "watch-1", "settings": {}, "config": {}}
    )

    assert sensor.native_value == "normal"
    assert sensor.options == ["normal", "schoolway", "explorer"]
    coordinator.tracking_mode.return_value = "UNKNOWN"
    assert sensor.native_value is None


def test_radar_configuration_and_remaining_time_entities() -> None:
    """Radar number defaults and diagnostic remaining time use their settings."""
    coordinator = Mock()
    coordinator.radar_duration.return_value = 15
    coordinator.radar_interval.return_value = 90
    coordinator.radar_remaining_seconds.return_value = 61
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    device = {"id": "watch-1", "settings": {}, "config": {}}

    duration = AnioRadarDurationNumber(coordinator, device)
    interval = AnioRadarIntervalNumber(coordinator, device)
    remaining = AnioRadarRemainingSensor(coordinator, device)
    radar_switch = AnioRadarSwitch(coordinator, device)
    bell_protection = AnioBellProtectionSwitch(coordinator, device)
    coordinator.radar_active.return_value = True
    coordinator.bell_protection_enabled.return_value = True

    assert duration.native_value == 15
    assert duration.native_min_value == 5
    assert duration.native_max_value == 20
    assert duration.entity_category is EntityCategory.CONFIG
    assert interval.native_value == 90
    assert interval.native_min_value == 60
    assert remaining.native_value == 2
    assert remaining.entity_category is EntityCategory.DIAGNOSTIC
    assert radar_switch.is_on
    assert bell_protection.is_on
    assert bell_protection.entity_category is EntityCategory.CONFIG


@pytest.mark.asyncio
async def test_find_my_device_is_blocked_by_default() -> None:
    """The default-on guard prevents a ringing request until deliberately disabled."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator._bell_protection = {}
    coordinator._api_lock = asyncio.Lock()
    coordinator.api = Mock(async_find_device=AsyncMock())

    assert coordinator.bell_protection_enabled("watch-1")
    with pytest.raises(HomeAssistantError) as err:
        await coordinator.async_find_device("watch-1")
    assert err.value.translation_key == "bell_protection_active"
    coordinator.api.async_find_device.assert_not_awaited()

    coordinator.set_bell_protection("watch-1", False)
    await coordinator.async_find_device("watch-1")
    coordinator.api.async_find_device.assert_awaited_once_with("watch-1")


@pytest.mark.asyncio
async def test_radar_start_requires_known_battery_at_least_twenty_percent() -> None:
    """Radar cannot start if battery telemetry is missing or below the threshold."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator._radar_sessions = {}
    coordinator._radar_durations = {"watch-1": 15}
    coordinator._radar_intervals = {"watch-1": 90}
    coordinator.data = {"watch-1": {"batteryLevel": 19}}
    coordinator.hass = Mock()
    coordinator._notify_entities = Mock()

    with pytest.raises(HomeAssistantError) as err:
        await coordinator.async_start_radar("watch-1")
    assert err.value.translation_key == "radar_battery_requirement"
    assert err.value.translation_placeholders == {"minimum": "20"}

    coordinator.data["watch-1"]["batteryLevel"] = 20
    coordinator.hass.async_create_task.side_effect = lambda coroutine, **kwargs: (
        coroutine.close()
    )
    await coordinator.async_start_radar("watch-1")
    assert coordinator.radar_active("watch-1")


@pytest.mark.asyncio
async def test_radar_stops_when_battery_falls_below_threshold() -> None:
    """An active Radar Mode session ends after a refreshed low-battery result."""
    coordinator = object.__new__(AnioCoordinator)
    now = dt_util.utcnow()
    session = RadarSession(now, now + timedelta(minutes=5), 60)
    coordinator._radar_sessions = {"watch-1": session}
    coordinator.data = {"watch-1": {"batteryLevel": 19}}
    coordinator._async_radar_cycle = AsyncMock()
    coordinator._notify_entities = Mock()

    await coordinator._async_run_radar("watch-1", session)

    coordinator._async_radar_cycle.assert_awaited_once_with("watch-1")
    assert not coordinator.radar_active("watch-1")


@pytest.mark.asyncio
async def test_radar_stops_and_warns_on_rate_limit(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """HTTP 429 ends Radar Mode cleanly and emits a warning."""
    coordinator = object.__new__(AnioCoordinator)
    now = dt_util.utcnow()
    session = RadarSession(now, now + timedelta(minutes=5), 60)
    coordinator._radar_sessions = {"watch-1": session}
    coordinator._async_radar_cycle = AsyncMock(
        side_effect=AnioRateLimitError("rate limited")
    )
    coordinator._notify_entities = Mock()

    await coordinator._async_run_radar("watch-1", session)

    assert not coordinator.radar_active("watch-1")
    assert "API rate limiting" in caplog.text


@pytest.mark.asyncio
async def test_radar_cycle_requests_then_waits_then_refreshes() -> None:
    """Each radar cycle completes the request before waiting and fetching data."""
    events: list[object] = []
    coordinator = object.__new__(AnioCoordinator)
    coordinator._api_lock = asyncio.Lock()
    coordinator.api = Mock(
        async_request_location_once=AsyncMock(
            side_effect=lambda device_id: events.append(("request", device_id))
        )
    )
    coordinator.last_update_success = True

    async def record_wait(seconds: int) -> None:
        events.append(("wait", seconds))

    async def record_refresh() -> None:
        events.append(("refresh",))

    coordinator.async_refresh = AsyncMock(side_effect=record_refresh)
    with patch(
        "custom_components.anio.coordinator.asyncio.sleep",
        new=AsyncMock(side_effect=record_wait),
    ):
        await coordinator._async_radar_cycle("watch-1")

    assert events == [
        ("request", "watch-1"),
        ("wait", 5),
        ("refresh",),
    ]


@pytest.mark.asyncio
async def test_radar_stops_at_hard_timeout() -> None:
    """An unresponsive radar cycle is cancelled when its session deadline expires."""
    coordinator = object.__new__(AnioCoordinator)
    now = dt_util.utcnow()
    session = RadarSession(now, now + timedelta(milliseconds=20), 60)
    coordinator._radar_sessions = {"watch-1": session}

    async def never_finishes(device_id: str) -> None:
        await asyncio.Event().wait()

    coordinator._async_radar_cycle = AsyncMock(side_effect=never_finishes)
    coordinator._notify_entities = Mock()

    await coordinator._async_run_radar("watch-1", session)

    assert not coordinator.radar_active("watch-1")


def test_radar_settings_reject_values_outside_supported_ranges() -> None:
    """Radar settings reject values outside their bounded entity controls."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator._radar_durations = {}
    coordinator._radar_intervals = {}

    with pytest.raises(HomeAssistantError):
        coordinator.set_radar_duration("watch-1", 4)
    with pytest.raises(HomeAssistantError):
        coordinator.set_radar_duration("watch-1", 21)
    with pytest.raises(HomeAssistantError):
        coordinator.set_radar_interval("watch-1", 59)

    coordinator.set_radar_duration("watch-1", 20)
    coordinator.set_radar_interval("watch-1", 60)
    assert coordinator.radar_duration("watch-1") == 20
    assert coordinator.radar_interval("watch-1") == 60
