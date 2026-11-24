"""Tests for Anio integration services."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml
from homeassistant.exceptions import HomeAssistantError

from custom_components.anio.const import ANIO_EMOJIS, DOMAIN
from custom_components.anio.coordinator import AnioCoordinator
from custom_components.anio.services import (
    async_refresh_activities,
    async_refresh_chat,
    async_send_emoji,
)


@pytest.mark.asyncio
async def test_send_emoji_resolves_the_selected_anio_device() -> None:
    """The service maps a Home Assistant device target to its Anio device ID."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.device_ids = {"watch-1"}
    coordinator.devices = [
        {
            "id": "watch-1",
            "settings": {"isChatEnabled": True},
            "config": {"hasEmojis": True},
        }
    ]
    coordinator.async_send_chat_emoji = AsyncMock()
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    registry = Mock()
    registry.async_get.return_value = SimpleNamespace(identifiers={(DOMAIN, "watch-1")})
    call = SimpleNamespace(
        hass=hass,
        data={"device_id": ["ha-device-1"], "emoji_code": " E09 "},
    )

    with patch("custom_components.anio.services.dr.async_get", return_value=registry):
        await async_send_emoji(call)

    coordinator.async_send_chat_emoji.assert_awaited_once_with("watch-1", "E09")


@pytest.mark.asyncio
async def test_refresh_chat_resolves_the_selected_anio_device() -> None:
    """The refresh service targets only the selected watch's chat."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.chat_device_ids = {"watch-1"}
    coordinator.async_refresh_chat = AsyncMock()
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    registry = Mock()
    registry.async_get.return_value = SimpleNamespace(identifiers={(DOMAIN, "watch-1")})
    call = SimpleNamespace(hass=hass, data={"device_id": ["ha-device-1"]})

    with patch("custom_components.anio.services.dr.async_get", return_value=registry):
        await async_refresh_chat(call)

    coordinator.async_refresh_chat.assert_awaited_once_with("watch-1")


@pytest.mark.asyncio
async def test_refresh_activities_selects_the_correct_account() -> None:
    """A watch target refreshes its account, with the requested cooldown behavior."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.device_ids = {"watch-1"}
    coordinator.async_refresh_activities = AsyncMock()
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    registry = Mock()
    registry.async_get.return_value = SimpleNamespace(identifiers={(DOMAIN, "watch-1")})
    call = SimpleNamespace(
        hass=hass, data={"device_id": ["ha-device-1"], "force": False}
    )
    with patch("custom_components.anio.services.dr.async_get", return_value=registry):
        await async_refresh_activities(call)
    coordinator.async_refresh_activities.assert_awaited_once_with(force=False)


@pytest.mark.asyncio
async def test_send_emoji_rejects_a_watch_without_emoji_support() -> None:
    """The service refuses to send codes to watches lacking emoji capability."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.device_ids = {"watch-1"}
    coordinator.devices = [
        {
            "id": "watch-1",
            "settings": {"isChatEnabled": True},
            "config": {"hasEmojis": False},
        }
    ]
    coordinator.async_send_chat_emoji = AsyncMock()
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    registry = Mock()
    registry.async_get.return_value = SimpleNamespace(identifiers={(DOMAIN, "watch-1")})
    call = SimpleNamespace(
        hass=hass,
        data={"device_id": ["ha-device-1"], "emoji_code": "E02"},
    )

    with (
        patch("custom_components.anio.services.dr.async_get", return_value=registry),
        pytest.raises(HomeAssistantError) as err,
    ):
        await async_send_emoji(call)

    assert err.value.translation_key == "emoji_chat_unavailable"
    coordinator.async_send_chat_emoji.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_emoji_rejects_unknown_code() -> None:
    """Only codes in the accepted emoji mapping can be sent by the service."""
    coordinator = object.__new__(AnioCoordinator)
    coordinator.device_ids = {"watch-1"}
    coordinator.devices = [
        {
            "id": "watch-1",
            "settings": {"isChatEnabled": True},
            "config": {"hasEmojis": True},
        }
    ]
    coordinator.async_send_chat_emoji = AsyncMock()
    hass = SimpleNamespace(data={DOMAIN: {"entry-1": coordinator}})
    registry = Mock()
    registry.async_get.return_value = SimpleNamespace(identifiers={(DOMAIN, "watch-1")})
    call = SimpleNamespace(
        hass=hass,
        data={"device_id": ["ha-device-1"], "emoji_code": "E10"},
    )

    with (
        patch("custom_components.anio.services.dr.async_get", return_value=registry),
        pytest.raises(HomeAssistantError) as err,
    ):
        await async_send_emoji(call)

    assert err.value.translation_key == "invalid_emoji_code"
    coordinator.async_send_chat_emoji.assert_not_awaited()


def test_emoji_service_options_match_the_runtime_mapping() -> None:
    """The service dropdown and the sendable code mapping remain in sync."""
    services_file = (
        Path(__file__).parents[1] / "custom_components" / "anio" / "services.yaml"
    )
    service_config = yaml.safe_load(services_file.read_text(encoding="utf-8"))
    options = service_config["send_emoji"]["fields"]["emoji_code"]["selector"][
        "select"
    ]["options"]

    assert {option["value"] for option in options} == set(ANIO_EMOJIS)


def test_translation_files_have_matching_keys() -> None:
    """The English base and both supported locales expose the same keys."""
    integration_path = Path(__file__).parents[1] / "custom_components" / "anio"
    translations = [
        json.loads((integration_path / "strings.json").read_text(encoding="utf-8")),
        json.loads(
            (integration_path / "translations" / "de.json").read_text(
                encoding="utf-8"
            )
        ),
        json.loads(
            (integration_path / "translations" / "en.json").read_text(
                encoding="utf-8"
            )
        ),
    ]

    def keys(value: object, prefix: str = "") -> set[str]:
        if not isinstance(value, dict):
            return {prefix}
        return {
            key
            for name, child in value.items()
            for key in keys(child, f"{prefix}.{name}" if prefix else name)
        }

    expected = keys(translations[0])
    assert keys(translations[1]) == expected
    assert keys(translations[2]) == expected
