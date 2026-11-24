"""Tests for the Anio API client."""

import uuid
from datetime import UTC, datetime
from typing import Any, Self
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.anio.api import (
    AnioApi,
    AnioApiError,
    AnioAuthError,
    AnioRateLimitError,
)
from custom_components.anio.const import API_BASE_URL

TEST_APP_UUID = uuid.uuid4().hex[:16]


class MockResponse:
    """Minimal aiohttp response context manager."""

    def __init__(self, status: int, payload: Any) -> None:
        self.status = status
        self.json = AsyncMock(return_value=payload)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_login_posts_credentials_and_returns_tokens() -> None:
    """The login request includes API headers and does not retain the password."""
    response = MockResponse(
        200,
        {"refreshToken": "refresh", "accessToken": "access"},
    )
    session = Mock()
    session.post.return_value = response
    api = AnioApi(session, TEST_APP_UUID)

    assert await api.async_login("person@example.com", "secret") == (
        "refresh",
        "access",
    )
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args == (f"{API_BASE_URL}/auth/login",)
    assert kwargs["json"] == {
        "email": "person@example.com",
        "password": "secret",
    }
    assert kwargs["headers"]["client-id"] == "ANIO"
    assert kwargs["headers"]["app-uuid"] == TEST_APP_UUID
    assert api.access_token == "access"


@pytest.mark.asyncio
async def test_refresh_uses_refresh_token_and_empty_body() -> None:
    """Refresh sends the refresh token as bearer auth with an empty body."""
    response = MockResponse(200, {"accessToken": "new-access"})
    session = Mock()
    session.post.return_value = response
    api = AnioApi(session, TEST_APP_UUID, "refresh")

    assert await api.async_refresh_access_token() == "new-access"
    kwargs = session.post.call_args.kwargs
    assert session.post.call_args.args == (f"{API_BASE_URL}/auth/refresh-access-token",)
    assert kwargs["headers"]["Authorization"] == "Bearer refresh"
    assert kwargs["data"] == b""


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials() -> None:
    """Unauthorized login responses become an authentication error."""
    session = Mock()
    session.post.return_value = MockResponse(401, {})
    api = AnioApi(session, TEST_APP_UUID)

    with pytest.raises(AnioAuthError):
        await api.async_login("person@example.com", "wrong")


@pytest.mark.asyncio
async def test_get_devices_refreshes_once_after_unauthorized_response() -> None:
    """An unauthorized devices request refreshes its token and retries once."""
    session = Mock()
    session.post.side_effect = [
        MockResponse(200, {"accessToken": "first-access"}),
        MockResponse(200, {"accessToken": "second-access"}),
    ]
    session.get.side_effect = [
        MockResponse(401, {}),
        MockResponse(200, [{"id": "watch-1"}]),
    ]
    api = AnioApi(session, TEST_APP_UUID, "refresh")

    assert await api.async_get_devices() == [{"id": "watch-1"}]
    assert session.post.call_count == 2
    assert session.get.call_count == 2
    assert session.get.call_args.kwargs["headers"]["Authorization"] == (
        "Bearer second-access"
    )


@pytest.mark.asyncio
async def test_get_devices_uses_existing_access_token() -> None:
    """The device list request sends the current access token."""
    session = Mock()
    session.get.return_value = MockResponse(200, [{"id": "watch-1"}])
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    assert await api.async_get_devices() == [{"id": "watch-1"}]
    session.get.assert_called_once()
    assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer access"


@pytest.mark.asyncio
async def test_get_last_locations_uses_authenticated_endpoint() -> None:
    """The latest-location request uses the access token and expected endpoint."""
    session = Mock()
    session.get.return_value = MockResponse(
        200,
        [{"id": "location-1", "position": [1.0, 2.0]}],
    )
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    assert await api.async_get_last_locations() == [
        {"id": "location-1", "position": [1.0, 2.0]}
    ]
    assert session.get.call_args.args == (f"{API_BASE_URL}/location/last",)
    assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer access"


@pytest.mark.asyncio
async def test_get_activities_uses_parameterless_authenticated_endpoint() -> None:
    """Fetch the account-wide list and reject malformed response shapes."""
    session = Mock()
    session.get.side_effect = [
        MockResponse(200, [{"id": "activity-1"}]),
        MockResponse(200, {"activities": []}),
    ]
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"
    assert await api.async_get_activities() == [{"id": "activity-1"}]
    assert session.get.call_args.args == (f"{API_BASE_URL}/activity",)
    assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer access"
    with pytest.raises(AnioApiError):
        await api.async_get_activities()


@pytest.mark.asyncio
async def test_send_chat_text_posts_the_expected_payload() -> None:
    """Text chat requests preserve the message and use the provided sender name."""
    session = Mock()
    session.post.return_value = MockResponse(201, {"id": "message-1"})
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    assert await api.async_send_chat_text(
        "watch-1", username="Alice Müller", text="Komm bitte nach Hause"
    ) == {"id": "message-1"}
    assert session.post.call_args.args == (f"{API_BASE_URL}/chat/message/text",)
    assert session.post.call_args.kwargs["json"] == {
        "username": "Alice Müller",
        "text": "Komm bitte nach Hause",
        "deviceId": "watch-1",
    }


@pytest.mark.asyncio
async def test_send_chat_emoji_posts_the_api_code() -> None:
    """Emoji requests send the supplied Anio code in the text field."""
    session = Mock()
    session.post.return_value = MockResponse(201, {"id": "message-emoji-1"})
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    assert await api.async_send_chat_emoji(
        "watch-1", username="HA", emoji_code="E02"
    ) == {"id": "message-emoji-1"}
    assert session.post.call_args.args == (f"{API_BASE_URL}/chat/message/emoji",)
    assert session.post.call_args.kwargs["json"] == {
        "username": "HA",
        "text": "E02",
        "deviceId": "watch-1",
    }


@pytest.mark.asyncio
async def test_get_chat_messages_encodes_the_since_timestamp() -> None:
    """Chat polling uses the watch endpoint and an encoded UTC cursor."""
    session = Mock()
    session.get.return_value = MockResponse(200, [{"id": "message-1"}])
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    assert await api.async_get_chat_messages(
        "watch-1",
        since=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    ) == [{"id": "message-1"}]
    assert session.get.call_args.args == (
        f"{API_BASE_URL}/chat/watch-1?since=2026-01-02T03%3A04%3A05Z",
    )


@pytest.mark.asyncio
async def test_request_location_once_posts_empty_body_and_accepts_204() -> None:
    """The one-time location command accepts the observed no-content response."""
    response = MockResponse(204, None)
    session = Mock()
    session.post.return_value = response
    api = AnioApi(session, TEST_APP_UUID, "refresh")
    api._access_token = "access"

    await api.async_request_location_once("watch-1")

    args, kwargs = session.post.call_args
    assert args == (f"{API_BASE_URL}/device/watch-1/cr",)
    assert kwargs["headers"]["Authorization"] == "Bearer access"
    assert kwargs["data"] == b""
    response.json.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_device_posts_to_watch_find_endpoint() -> None:
    """Find My Device sends an empty POST to the selected watch."""
    session = Mock()
    session.post.return_value = MockResponse(204, None)
    api = AnioApi(session, TEST_APP_UUID, "refresh")
    api._access_token = "access"

    await api.async_find_device("watch-1")

    args, kwargs = session.post.call_args
    assert args == (f"{API_BASE_URL}/device/watch-1/find",)
    assert kwargs["headers"]["Authorization"] == "Bearer access"
    assert "data" not in kwargs
    assert "json" not in kwargs


@pytest.mark.asyncio
async def test_rate_limit_has_a_specific_api_error() -> None:
    """HTTP 429 can be distinguished so Radar Mode can stop safely."""
    session = Mock()
    session.get.return_value = MockResponse(429, {})
    api = AnioApi(session, TEST_APP_UUID)
    api._access_token = "access"

    with pytest.raises(AnioRateLimitError):
        await api.async_get_last_locations()


@pytest.mark.asyncio
async def test_request_location_once_refreshes_after_unauthorized() -> None:
    """The location command is retried once with a refreshed access token."""
    session = Mock()
    session.post.side_effect = [
        MockResponse(401, {}),
        MockResponse(200, {"accessToken": "new-access"}),
        MockResponse(204, None),
    ]
    api = AnioApi(session, TEST_APP_UUID, "refresh")
    api._access_token = "expired-access"

    await api.async_request_location_once("watch-1")

    assert session.post.call_count == 3
    assert session.post.call_args.kwargs["headers"]["Authorization"] == (
        "Bearer new-access"
    )


@pytest.mark.asyncio
async def test_set_explorer_posts_activate_flag_and_validates_response() -> None:
    """Explorer activation sends the captured JSON body and returns its state."""
    response_data = {
        "deviceId": "watch-1",
        "active": True,
        "deviceLocatingInterval": "SIXTY_MINUTES",
    }
    session = Mock()
    session.post.return_value = MockResponse(201, response_data)
    api = AnioApi(session, TEST_APP_UUID, "refresh")
    api._access_token = "access"

    assert await api.async_set_explorer("watch-1", activate=True) == response_data
    args, kwargs = session.post.call_args
    assert args == (f"{API_BASE_URL}/explorer",)
    assert kwargs["json"] == {"deviceId": "watch-1", "activate": True}
    assert kwargs["headers"]["Authorization"] == "Bearer access"
