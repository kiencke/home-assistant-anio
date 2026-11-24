"""Tests for the Anio config flow."""

import re
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from custom_components.anio.api import AnioAuthError
from custom_components.anio.config_flow import (
    AnioConfigFlow,
    _resolve_app_uuid,
    _user_schema,
)
from custom_components.anio.config_flow import (
    vol as config_flow_vol,
)
from custom_components.anio.const import (
    CONF_ACTIVITY_INTERVAL,
    CONF_APP_UUID,
    CONF_EXPLORER_INTERVAL,
    CONF_NORMAL_INTERVAL,
    CONF_REFRESH_TOKEN,
    CONF_SCHOOLWAY_INTERVAL,
    DEFAULT_ACTIVITY_INTERVAL_MINUTES,
    DEFAULT_EXPLORER_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

TEST_APP_UUID = uuid.uuid4().hex[:16]


def test_user_schema_prefills_optional_app_uuid() -> None:
    """The login form's optional UUID field has a generated default."""
    app_uuid = TEST_APP_UUID
    values = _user_schema(app_uuid)(
        {CONF_EMAIL: "person@example.com", CONF_PASSWORD: "secret"}
    )

    assert values[CONF_APP_UUID] == app_uuid


def test_config_flow_generates_16_character_hex_app_uuid() -> None:
    """Each flow starts with a generated UUID suitable for the API header."""
    assert re.fullmatch(r"[0-9a-f]{16}", AnioConfigFlow()._app_uuid)


def test_empty_app_uuid_generates_a_new_value() -> None:
    """An explicitly blank app UUID is replaced with a generated value."""
    assert re.fullmatch(r"[0-9a-f]{16}", _resolve_app_uuid(""))


def test_custom_app_uuid_is_normalized() -> None:
    """Custom hexadecimal app UUIDs are normalized for consistent storage."""
    app_uuid = f"A{TEST_APP_UUID[1:15]}B"
    assert _resolve_app_uuid(app_uuid) == app_uuid.lower()


def test_invalid_app_uuid_is_rejected_by_validator() -> None:
    """Custom app UUID values must contain exactly 16 hexadecimal characters."""
    with pytest.raises(config_flow_vol.Invalid):
        _resolve_app_uuid("invalid")


@pytest.mark.asyncio
async def test_user_login_stores_only_refresh_token(hass) -> None:
    """A successful login creates an entry without persisting credentials."""
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        api_class.return_value.async_login = AsyncMock(
            return_value=("refresh-token", "access-token")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        generated_app_uuid = result["data_schema"](
            {
                CONF_EMAIL: " Person@Example.com ",
                CONF_PASSWORD: "secret",
            }
        )[CONF_APP_UUID]
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: " Person@Example.com ",
                CONF_PASSWORD: "secret",
            },
        )

    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "person@example.com"
    assert entry.data[CONF_EMAIL] == "Person@Example.com"
    assert entry.data[CONF_REFRESH_TOKEN] == "refresh-token"
    assert entry.options == {
        CONF_ACTIVITY_INTERVAL: DEFAULT_ACTIVITY_INTERVAL_MINUTES,
        CONF_NORMAL_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_SCHOOLWAY_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_EXPLORER_INTERVAL: DEFAULT_EXPLORER_SCAN_INTERVAL,
    }
    assert CONF_APP_UUID in entry.data
    assert re.fullmatch(r"[0-9a-f]{16}", entry.data[CONF_APP_UUID])
    assert entry.data[CONF_APP_UUID] == generated_app_uuid
    assert api_class.call_args.kwargs["app_uuid"] == entry.data[CONF_APP_UUID]
    assert CONF_PASSWORD not in entry.data
    assert "access_token" not in entry.data


@pytest.mark.asyncio
async def test_blank_app_uuid_uses_generated_default(hass) -> None:
    """Leaving the optional app UUID blank uses the flow's generated value."""
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        api_class.return_value.async_login = AsyncMock(
            return_value=("refresh-token", "access-token")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: "person@example.com",
                CONF_PASSWORD: "secret",
                CONF_APP_UUID: "",
            },
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert result["type"] == "create_entry"
    assert re.fullmatch(r"[0-9a-f]{16}", entry.data[CONF_APP_UUID])
    assert api_class.call_args.kwargs["app_uuid"] == entry.data[CONF_APP_UUID]


@pytest.mark.asyncio
async def test_custom_app_uuid_is_normalized_and_persisted(hass) -> None:
    """A user-provided 16-character hexadecimal UUID is retained in lowercase."""
    app_uuid = f"A{TEST_APP_UUID[1:15]}B"
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        api_class.return_value.async_login = AsyncMock(
            return_value=("refresh-token", "access-token")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: "person@example.com",
                CONF_PASSWORD: "secret",
                CONF_APP_UUID: app_uuid,
            },
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert result["type"] == "create_entry"
    assert entry.data[CONF_APP_UUID] == app_uuid.lower()
    assert api_class.call_args.kwargs["app_uuid"] == app_uuid.lower()


@pytest.mark.asyncio
async def test_invalid_app_uuid_is_rejected(hass) -> None:
    """Invalid custom UUIDs are rejected before making an API request."""
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: "person@example.com",
                CONF_PASSWORD: "secret",
                CONF_APP_UUID: "not-an-app-uuid",
            },
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_app_uuid"}
    api_class.assert_not_called()
    assert not hass.config_entries.async_entries(DOMAIN)


@pytest.mark.asyncio
async def test_invalid_login_shows_auth_error(hass) -> None:
    """Invalid credentials leave the flow open with a translated error key."""
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        api_class.return_value.async_login = AsyncMock(
            side_effect=AnioAuthError("unauthorized")
        )
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_EMAIL: "person@example.com",
                CONF_PASSWORD: "wrong",
            },
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}
    assert not hass.config_entries.async_entries(DOMAIN)


@pytest.mark.asyncio
async def test_duplicate_email_is_normalized(hass) -> None:
    """The same email with different case cannot create a second entry."""
    with patch("custom_components.anio.config_flow.AnioApi") as api_class:
        api_class.return_value.async_login = AsyncMock(
            return_value=("refresh-token", "access-token")
        )
        first = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        await hass.config_entries.flow.async_configure(
            first["flow_id"],
            user_input={
                CONF_EMAIL: "person@example.com",
                CONF_PASSWORD: "secret",
            },
        )
        second = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            second["flow_id"],
            user_input={
                CONF_EMAIL: "PERSON@example.com",
                CONF_PASSWORD: "secret",
            },
        )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
    assert api_class.return_value.async_login.await_count == 1
