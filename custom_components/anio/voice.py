"""Authenticated HTTP endpoints for Anio chat audio."""

from http import HTTPStatus
from typing import Any

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import AnioCoordinator, supports_chat_voice

MAX_VOICE_UPLOAD_BYTES = 8 * 1024 * 1024


class AnioVoiceFormatNotConfigured(Exception):
    """Raised until the Anio voice codec and API request are verified."""


async def async_convert_voice_audio(
    audio_data: bytes, content_type: str
) -> tuple[bytes, str]:
    """Conversion seam for the verified Anio voice format."""
    raise AnioVoiceFormatNotConfigured(
        "The Anio voice codec and upload API have not been verified"
    )


class AnioVoiceProxyView(HomeAssistantView):
    """Provide an authenticated endpoint for incoming voice messages."""

    url = "/api/anio/voice/{device_id}/{message_id}"
    name = "api:anio:voice:proxy"
    requires_auth = True

    async def get(
        self, request: web.Request, device_id: str, message_id: str
    ) -> web.Response:
        """Return a clear not-implemented response until the audio API is known."""
        watch = _get_watch(request.app["hass"], device_id)
        if watch is None:
            return self.json_message(
                "The Anio watch was not found.",
                HTTPStatus.NOT_FOUND,
                message_code="device_not_found",
            )

        coordinator, _device = watch
        message = coordinator.chat_message(device_id, message_id)
        if (
            message is None
            or not message.is_from_watch
            or message.message_type != "VOICE"
        ):
            return self.json_message(
                "The voice message was not found.",
                HTTPStatus.NOT_FOUND,
                message_code="voice_message_not_found",
            )

        return self.json_message(
            "The Anio audio source has not been verified yet.",
            HTTPStatus.NOT_IMPLEMENTED,
            message_code="voice_source_not_verified",
        )


class AnioVoiceUploadView(HomeAssistantView):
    """Accept outgoing voice uploads only after the codec/API is verified."""

    url = "/api/anio/voice/{device_id}/send"
    name = "api:anio:voice:upload"
    requires_auth = True

    async def post(self, request: web.Request, device_id: str) -> web.Response:
        """Return a clear not-implemented response without retaining audio."""
        watch = _get_watch(request.app["hass"], device_id)
        if watch is None:
            return self.json_message(
                "The Anio watch was not found.",
                HTTPStatus.NOT_FOUND,
                message_code="device_not_found",
            )

        _coordinator, device = watch
        if not supports_chat_voice(device):
            return self.json_message(
                "This Anio watch does not support voice chat.",
                HTTPStatus.CONFLICT,
                message_code="voice_chat_unsupported",
            )

        if not request.content_type.startswith("audio/"):
            return self.json_message(
                "The upload must use an audio content type.",
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                message_code="audio_required",
            )
        if (
            request.content_length is not None
            and request.content_length > MAX_VOICE_UPLOAD_BYTES
        ):
            return self.json_message(
                "The audio file exceeds the maximum size.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                message_code="audio_too_large",
            )

        audio_data = await _read_limited_upload(request)
        if audio_data is None:
            return self.json_message(
                "The audio file exceeds the maximum size.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                message_code="audio_too_large",
            )
        try:
            await async_convert_voice_audio(audio_data, request.content_type)
        except AnioVoiceFormatNotConfigured as err:
            return self.json_message(
                str(err),
                HTTPStatus.NOT_IMPLEMENTED,
                message_code="voice_format_not_configured",
            )
        return self.json_message(
            "The Anio audio upload has not been implemented yet.",
            HTTPStatus.NOT_IMPLEMENTED,
            message_code="voice_upload_not_implemented",
        )


def _get_watch(
    hass: HomeAssistant, device_id: str
) -> tuple[AnioCoordinator, dict[str, Any]] | None:
    """Find a loaded Anio watch by its API ID."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, AnioCoordinator):
            continue
        device = next(
            (
                item
                for item in coordinator.devices
                if isinstance(item.get("id"), str) and item["id"].strip() == device_id
            ),
            None,
        )
        if device is not None:
            return coordinator, device
    return None


async def _read_limited_upload(request: web.Request) -> bytes | None:
    """Read an upload up to the configured in-memory size limit."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.content.iter_chunked(64 * 1024):
        size += len(chunk)
        if size > MAX_VOICE_UPLOAD_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)
