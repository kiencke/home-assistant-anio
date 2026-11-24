"""Asynchronous client for the Anio Cloud API."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlencode

from aiohttp import ClientError, ClientSession
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    API_CLIENT_ID,
    API_LANGUAGE,
    API_USER_AGENT,
)


class AnioApiError(Exception):
    """Base error for Anio API failures."""


class AnioAuthError(AnioApiError):
    """Authentication with the Anio API failed."""


class AnioUnauthorizedError(AnioAuthError):
    """The Anio API rejected an access token."""


class AnioConnectionError(AnioApiError):
    """The Anio API could not be reached or returned a server error."""


class AnioRateLimitError(AnioApiError):
    """The Anio API rate limit was reached."""


class AnioApi:
    """Client for the Anio Cloud API."""

    def __init__(
        self,
        session: ClientSession,
        app_uuid: str,
        refresh_token: str | None = None,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._app_uuid = app_uuid
        self._refresh_token = refresh_token
        self._access_token: str | None = None

    @property
    def access_token(self) -> str | None:
        """Return the current in-memory access token."""
        return self._access_token

    async def async_login(self, email: str, password: str) -> tuple[str, str]:
        """Log in and return the refresh and access tokens."""
        response = await self._async_post(
            "/auth/login",
            json_body={"email": email, "password": password},
        )
        refresh_token = response.get("refreshToken")
        access_token = response.get("accessToken")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise AnioApiError("Login response did not contain a refresh token")
        if not isinstance(access_token, str) or not access_token:
            raise AnioApiError("Login response did not contain an access token")

        self._refresh_token = refresh_token
        self._access_token = access_token
        return refresh_token, access_token

    async def async_refresh_access_token(self) -> str:
        """Refresh the access token using the stored refresh token."""
        if not self._refresh_token:
            raise AnioAuthError("No refresh token is available")

        response = await self._async_post(
            "/auth/refresh-access-token",
            authorization=self._refresh_token,
            empty_body=True,
        )
        access_token = response.get("accessToken")
        if not isinstance(access_token, str) or not access_token:
            raise AnioApiError("Refresh response did not contain an access token")

        self._access_token = access_token
        return access_token

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Return the devices linked to the account."""
        return await self._async_get_list("/device/list")

    async def async_get_last_locations(self) -> list[dict[str, Any]]:
        """Return the latest location records."""
        return await self._async_get_list("/location/last")

    async def async_get_activities(self) -> list[dict[str, Any]]:
        """Return the account's activity records."""
        return await self._async_get_list("/activity")

    async def async_send_chat_text(
        self, device_id: str, *, username: str, text: str
    ) -> dict[str, Any]:
        """Send a text chat message to a watch."""
        device_id = device_id.strip()
        if not device_id or not username.strip() or not text.strip():
            raise AnioApiError("Anio chat message is missing required data")

        payload = await self._async_authenticated_request(
            "POST",
            "/chat/message/text",
            json_body={"username": username, "text": text, "deviceId": device_id},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise AnioApiError("Anio returned an invalid chat message response")
        return payload

    async def async_send_chat_emoji(
        self, device_id: str, *, username: str, emoji_code: str
    ) -> dict[str, Any]:
        """Send an emoji identified by its Anio API code to a watch."""
        device_id = device_id.strip()
        if not device_id or not username.strip() or not emoji_code.strip():
            raise AnioApiError("Anio chat emoji is missing required data")

        payload = await self._async_authenticated_request(
            "POST",
            "/chat/message/emoji",
            json_body={
                "username": username,
                "text": emoji_code,
                "deviceId": device_id,
            },
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise AnioApiError("Anio returned an invalid chat emoji response")
        return payload

    async def async_get_chat_messages(
        self, device_id: str, *, since: datetime
    ) -> list[dict[str, Any]]:
        """Return chat messages for a watch created after the given timestamp."""
        device_id = device_id.strip()
        if not device_id:
            raise AnioApiError("Anio device ID is missing")

        timestamp = dt_util.as_utc(since).isoformat(timespec="seconds")
        if timestamp.endswith("+00:00"):
            timestamp = f"{timestamp[:-6]}Z"
        path = f"/chat/{quote(device_id, safe='')}?{urlencode({'since': timestamp})}"
        return await self._async_get_list(path)

    async def async_request_location_once(self, device_id: str) -> None:
        """Ask a watch for a one-time location update."""
        device_id = device_id.strip()
        if not device_id:
            raise AnioApiError("Anio device ID is missing")

        payload = await self._async_authenticated_request(
            "POST",
            f"/device/{quote(device_id, safe='')}/cr",
            empty_body=True,
        )
        if payload is not None:
            raise AnioApiError("Anio returned an unexpected location request response")

    async def async_find_device(self, device_id: str) -> None:
        """Ask a watch to ring so it can be found nearby."""
        device_id = device_id.strip()
        if not device_id:
            raise AnioApiError("Anio device ID is missing")

        await self._async_authenticated_request(
            "POST",
            f"/device/{quote(device_id, safe='')}/find",
        )

    async def async_set_explorer(
        self, device_id: str, *, activate: bool
    ) -> dict[str, Any]:
        """Activate or deactivate Explorer tracking for a watch."""
        device_id = device_id.strip()
        if not device_id:
            raise AnioApiError("Anio device ID is missing")

        payload = await self._async_authenticated_request(
            "POST",
            "/explorer",
            json_body={"deviceId": device_id, "activate": activate},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get("active"), bool):
            raise AnioApiError("Anio returned an invalid Explorer response")
        return payload

    async def _async_get_list(self, path: str) -> list[dict[str, Any]]:
        """Fetch a list endpoint, refreshing an expired access token once."""
        payload = await self._async_authenticated_request("GET", path)
        if not isinstance(payload, list) or not all(
            isinstance(device, dict) for device in payload
        ):
            raise AnioApiError(f"Anio API returned an unexpected response for {path}")
        return payload

    async def _async_authenticated_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        empty_body: bool = False,
    ) -> Any:
        """Send an authenticated request, refreshing an expired token once."""
        access_token = self._access_token
        if not access_token:
            access_token = await self.async_refresh_access_token()

        try:
            return await self._async_request(
                method,
                path,
                json_body=json_body,
                authorization=access_token,
                empty_body=empty_body,
            )
        except AnioUnauthorizedError:
            access_token = await self.async_refresh_access_token()
            return await self._async_request(
                method,
                path,
                json_body=json_body,
                authorization=access_token,
                empty_body=empty_body,
            )

    async def _async_post(
        self,
        path: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        authorization: str | None = None,
        empty_body: bool = False,
    ) -> dict[str, Any]:
        """Send an API POST request and decode its JSON response."""
        payload = await self._async_request(
            "POST",
            path,
            json_body=json_body,
            authorization=authorization,
            empty_body=empty_body,
        )
        if not isinstance(payload, dict):
            raise AnioApiError("Anio API returned an unexpected response")
        return payload

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        authorization: str | None = None,
        empty_body: bool = False,
    ) -> Any:
        """Send an API request and decode its JSON response."""
        headers = {
            "client-id": API_CLIENT_ID,
            "app-uuid": self._app_uuid,
            "user-agent": API_USER_AGENT,
            "accept-language": API_LANGUAGE,
        }
        request_data: dict[str, Any] = {}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
            request_data["json"] = dict(json_body)
        if authorization is not None:
            headers["Authorization"] = f"Bearer {authorization}"
        if empty_body:
            request_data["data"] = b""

        try:
            request = self._session.get if method == "GET" else self._session.post
            async with request(
                f"{API_BASE_URL}{path}", headers=headers, **request_data
            ) as response:
                if response.status == 401:
                    raise AnioUnauthorizedError("Anio API rejected the access token")
                if response.status == 403:
                    raise AnioAuthError("Anio API rejected the credentials")
                if response.status == 429:
                    raise AnioRateLimitError("Anio API rate limit was reached")
                if response.status >= 500:
                    raise AnioConnectionError(
                        f"Anio API returned HTTP {response.status}"
                    )
                if response.status >= 400:
                    raise AnioApiError(f"Anio API returned HTTP {response.status}")
                if response.status == 204:
                    return None
                try:
                    payload = await response.json(content_type=None)
                except (ClientError, ValueError) as err:
                    raise AnioApiError("Anio API returned invalid JSON") from err
        except (ClientError, TimeoutError) as err:
            raise AnioConnectionError("Could not connect to the Anio API") from err

        return payload
