"""Support for Anio children's watches."""

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api import AnioApi, AnioApiError, AnioAuthError, AnioConnectionError
from .const import CONF_APP_UUID, CONF_REFRESH_TOKEN, DOMAIN, PLATFORMS
from .coordinator import AnioCoordinator
from .entity import get_device_info
from .services import async_setup_services
from .voice import AnioVoiceProxyView, AnioVoiceUploadView

_CHAT_CARD_URL = "/api/anio/www/anio-chat-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Anio services, views, and the bundled chat card."""
    async_setup_services(hass)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                _CHAT_CARD_URL,
                str(Path(__file__).parent / "www" / "anio-chat-card.js"),
                cache_headers=False,
            )
        ]
    )
    frontend.add_extra_js_url(hass, _CHAT_CARD_URL)
    hass.http.register_view(AnioVoiceProxyView())
    hass.http.register_view(AnioVoiceUploadView())
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Anio, register its watches, and load their entities."""
    api = AnioApi(
        session=async_get_clientsession(hass),
        app_uuid=entry.data[CONF_APP_UUID],
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
    )
    try:
        await api.async_refresh_access_token()
        devices = await api.async_get_devices()
    except AnioAuthError as err:
        raise ConfigEntryAuthFailed("Anio refresh token is invalid") from err
    except AnioConnectionError as err:
        raise ConfigEntryNotReady("Could not connect to the Anio API") from err
    except AnioApiError as err:
        raise ConfigEntryNotReady("Anio returned an invalid API response") from err

    try:
        device_info = [get_device_info(device) for device in devices]
    except AnioApiError as err:
        raise ConfigEntryNotReady("Anio returned invalid device metadata") from err

    coordinator = AnioCoordinator(hass, api, entry, devices)
    await coordinator.async_load_chat_history()
    await coordinator.async_load_activity_history()
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_scheduled_activity_refresh()

    device_registry = dr.async_get(hass)
    for info in device_info:
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            **info,
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        async_track_time_interval(
            hass,
            coordinator.async_scheduled_activity_refresh,
            coordinator.activity_interval,
        )
    )
    entry.async_on_unload(coordinator.async_cancel_activity_refresh)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload Anio after options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Anio config entry and its platforms."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
