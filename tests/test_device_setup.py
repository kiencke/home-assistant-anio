"""Tests for Anio device registration during setup."""

import importlib
import json
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components import frontend
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.anio import async_setup, async_setup_entry
from custom_components.anio.const import (
    CONF_APP_UUID,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)

TEST_APP_UUID = uuid.uuid4().hex[:16]


@pytest.mark.asyncio
async def test_all_entities_have_translated_names() -> None:
    """Every platform creates entities with names translated in both languages."""
    coordinator = Mock()
    coordinator.devices = [
        {
            "id": "watch-1",
            "settings": {"isChatEnabled": True},
            "config": {"hasTextChat": True, "hasEmojis": True, "hasVoiceChat": True},
        }
    ]
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    entry = SimpleNamespace(entry_id="entry-1")
    base = Path(__file__).parents[1] / "custom_components" / "anio"
    paths = [
        base / "strings.json",
        base / "translations" / "en.json",
        base / "translations" / "de.json",
    ]
    translations = [json.loads(path.read_text(encoding="utf-8")) for path in paths]

    for platform in PLATFORMS:
        entities = []
        module = importlib.import_module(f"custom_components.anio.{platform}")
        await module.async_setup_entry(
            hass, entry, lambda items: entities.extend(items)
        )
        assert entities
        for entity in entities:
            assert entity.has_entity_name
            assert entity.translation_key
            assert not hasattr(entity, "_attr_name")
            for translation in translations:
                expected = translation["entity"][platform][entity.translation_key][
                    "name"
                ]
                key = (
                    f"component.{DOMAIN}.entity.{platform}."
                    f"{entity.translation_key}.name"
                )
                entity.platform_data = SimpleNamespace(
                    platform_name=DOMAIN,
                    domain=platform,
                    component_translations={},
                    platform_translations={key: expected},
                )
                entity.__dict__.pop("name", None)
                assert entity.name == expected


def test_entity_translation_keys_match() -> None:
    """English source and both translations cover the same entity keys."""
    base = Path(__file__).parents[1] / "custom_components" / "anio"
    source, english, german = [
        json.loads(path.read_text(encoding="utf-8"))["entity"]
        for path in (
            base / "strings.json",
            base / "translations" / "en.json",
            base / "translations" / "de.json",
        )
    ]
    assert source == english
    assert source.keys() == german.keys()
    for platform in source:
        assert source[platform].keys() == german[platform].keys()
        assert all(item.get("name") for item in german[platform].values())


@pytest.mark.asyncio
async def test_setup_registers_chat_card_and_authenticated_voice_views() -> None:
    """The integration loads its card and registers authenticated voice routes."""
    extra_js_urls = Mock()
    hass = SimpleNamespace(
        data={frontend.DATA_EXTRA_MODULE_URL: extra_js_urls},
        services=SimpleNamespace(async_register=Mock()),
        http=SimpleNamespace(
            async_register_static_paths=AsyncMock(),
            register_view=Mock(),
        ),
    )

    assert await async_setup(hass, {})

    static_config = hass.http.async_register_static_paths.await_args.args[0][0]
    assert static_config.url_path == "/api/anio/www/anio-chat-card.js"
    assert Path(static_config.path).is_file()
    assert static_config.cache_headers is False
    extra_js_urls.add.assert_called_once_with(static_config.url_path)
    views = [call.args[0] for call in hass.http.register_view.call_args_list]
    assert {type(view).__name__ for view in views} == {
        "AnioVoiceProxyView",
        "AnioVoiceUploadView",
    }
    assert all(view.requires_auth for view in views)


@pytest.mark.asyncio
async def test_setup_registers_each_watch_without_private_attributes() -> None:
    """Each Anio device gets a stable identifier and safe display metadata."""
    devices = [
        {
            "id": "watch-1",
            "imei": "private-imei",
            "settings": {
                "name": "Watch One",
                "phoneNr": "private-number",
                "smsPassword": "private-password",
            },
            "config": {
                "type": "WATCH",
                "generation": "6",
                "firmwareVersion": "firmware-1",
            },
        },
        {
            "id": "watch-2",
            "imei": "private-imei-2",
            "settings": {},
            "config": {},
        },
    ]
    hass = SimpleNamespace(
        data={},
        config_entries=Mock(async_forward_entry_setups=AsyncMock(return_value=None)),
    )
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={CONF_APP_UUID: TEST_APP_UUID, CONF_REFRESH_TOKEN: "refresh"},
        async_on_unload=Mock(),
        add_update_listener=Mock(return_value=lambda: None),
    )
    api = Mock()
    api.async_refresh_access_token = AsyncMock()
    api.async_get_devices = AsyncMock(return_value=devices)
    coordinator = Mock()
    coordinator.devices = devices
    coordinator.async_load_chat_history = AsyncMock()
    coordinator.async_load_activity_history = AsyncMock()
    coordinator.async_scheduled_activity_refresh = AsyncMock()
    coordinator.activity_interval = timedelta(minutes=60)
    coordinator.async_config_entry_first_refresh = AsyncMock()
    registry = Mock()

    with (
        patch("custom_components.anio.async_get_clientsession"),
        patch("custom_components.anio.AnioApi", return_value=api),
        patch("custom_components.anio.AnioCoordinator", return_value=coordinator),
        patch("custom_components.anio.dr.async_get", return_value=registry),
        patch("custom_components.anio.async_track_time_interval") as track_interval,
    ):
        assert await async_setup_entry(hass, entry)

    assert registry.async_get_or_create.call_count == 2
    first, second = [
        call.kwargs for call in registry.async_get_or_create.call_args_list
    ]
    assert first == {
        "config_entry_id": "entry-1",
        "identifiers": {(DOMAIN, "watch-1")},
        "manufacturer": "Anio",
        "name": "Watch One",
        "model": "WATCH Generation 6",
        "sw_version": "firmware-1",
    }
    assert second["identifiers"] == {(DOMAIN, "watch-2")}
    assert second["name"] == "Anio Watch watch-2"
    assert "imei" not in first
    assert "registrationCode" not in first
    assert "phoneNr" not in first
    assert "smsPassword" not in first
    assert "user" not in first
    assert hass.data[DOMAIN]["entry-1"] is coordinator
    api.async_refresh_access_token.assert_awaited_once()
    api.async_get_devices.assert_awaited_once()
    coordinator.async_load_chat_history.assert_awaited_once()
    coordinator.async_load_activity_history.assert_awaited_once()
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    coordinator.async_scheduled_activity_refresh.assert_awaited_once_with()
    track_interval.assert_called_once_with(
        hass, coordinator.async_scheduled_activity_refresh, timedelta(minutes=60)
    )
    assert track_interval.return_value in [
        call.args[0] for call in entry.async_on_unload.call_args_list
    ]


@pytest.mark.asyncio
async def test_setup_rejects_device_without_an_id() -> None:
    """Malformed device records fail setup instead of creating unstable devices."""
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={CONF_APP_UUID: TEST_APP_UUID, CONF_REFRESH_TOKEN: "refresh"},
        async_on_unload=Mock(),
        add_update_listener=Mock(return_value=lambda: None),
    )
    api = Mock()
    api.async_refresh_access_token = AsyncMock()
    api.async_get_devices = AsyncMock(return_value=[{"settings": {"name": "Watch"}}])
    registry = Mock()

    with (
        patch("custom_components.anio.async_get_clientsession"),
        patch("custom_components.anio.AnioApi", return_value=api),
        patch("custom_components.anio.dr.async_get", return_value=registry),
        pytest.raises(ConfigEntryNotReady, match="invalid device metadata"),
    ):
        await async_setup_entry(hass, entry)

    registry.async_get_or_create.assert_not_called()
