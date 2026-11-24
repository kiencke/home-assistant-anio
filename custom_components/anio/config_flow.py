"""Config flow for the Anio integration."""

import re
import uuid
from collections.abc import Callable, Mapping
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import AnioApi, AnioApiError, AnioAuthError, AnioConnectionError
from .const import (
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
    MAX_ACTIVITY_INTERVAL_MINUTES,
    MAX_SCAN_INTERVAL,
    MIN_ACTIVITY_INTERVAL_MINUTES,
    MIN_SCAN_INTERVAL,
    SCAN_INTERVAL_STEP,
)


def _user_schema(default_app_uuid: str) -> vol.Schema:
    """Build the login form with a generated, editable app UUID."""
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL)
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.PASSWORD,
                    autocomplete="current-password",
                )
            ),
            vol.Optional(CONF_APP_UUID, default=default_app_uuid): TextSelector(
                TextSelectorConfig(type=TextSelectorType.TEXT)
            ),
        }
    )


def _resolve_app_uuid(value: Any) -> str:
    """Validate a custom UUID or generate one when the field is empty."""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise vol.Invalid("App UUID must be text")

    value = value.strip()
    if not value:
        return uuid.uuid4().hex[:16]
    if re.fullmatch(r"[0-9a-fA-F]{16}", value) is None:
        raise vol.Invalid("App UUID must contain exactly 16 hexadecimal characters")
    return value.lower()


REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        )
    }
)


class AnioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Anio config and reauthentication flows."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._app_uuid = uuid.uuid4().hex[:16]
        self._reauth_entry: ConfigEntry | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the polling options flow."""
        return AnioOptionsFlow()

    async def _async_login(
        self, email: str, password: str, app_uuid: str
    ) -> tuple[str, str]:
        """Validate credentials against the Anio API."""
        api = AnioApi(
            session=async_get_clientsession(self.hass),
            app_uuid=app_uuid,
        )
        return await api.async_login(email, password)

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(self._app_uuid),
            )

        email = user_input[CONF_EMAIL].strip()
        await self.async_set_unique_id(email.lower())
        self._abort_if_unique_id_configured()

        if CONF_APP_UUID not in user_input:
            app_uuid = self._app_uuid
        else:
            try:
                app_uuid = _resolve_app_uuid(user_input[CONF_APP_UUID])
            except vol.Invalid:
                return self.async_show_form(
                    step_id="user",
                    data_schema=_user_schema(self._app_uuid),
                    errors={"base": "invalid_app_uuid"},
                )
        self._app_uuid = app_uuid

        errors: dict[str, str] = {}
        try:
            refresh_token, _ = await self._async_login(
                email,
                user_input[CONF_PASSWORD],
                app_uuid,
            )
        except AnioAuthError:
            errors["base"] = "invalid_auth"
        except AnioConnectionError:
            errors["base"] = "cannot_connect"
        except AnioApiError:
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(self._app_uuid),
                errors=errors,
            )

        return self.async_create_entry(
            title=email,
            data={
                CONF_EMAIL: email,
                CONF_APP_UUID: app_uuid,
                CONF_REFRESH_TOKEN: refresh_token,
            },
            options={
                CONF_ACTIVITY_INTERVAL: DEFAULT_ACTIVITY_INTERVAL_MINUTES,
                CONF_NORMAL_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_SCHOOLWAY_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_EXPLORER_INTERVAL: DEFAULT_EXPLORER_SCAN_INTERVAL,
            },
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication for an existing entry."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_not_found")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a password and replace the expired refresh token."""
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_entry_not_found")

        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
                description_placeholders={"email": self._reauth_entry.data[CONF_EMAIL]},
            )

        errors: dict[str, str] = {}
        try:
            refresh_token, _ = await self._async_login(
                self._reauth_entry.data[CONF_EMAIL],
                user_input[CONF_PASSWORD],
                self._reauth_entry.data[CONF_APP_UUID],
            )
        except AnioAuthError:
            errors["base"] = "invalid_auth"
        except AnioConnectionError:
            errors["base"] = "cannot_connect"
        except AnioApiError:
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=REAUTH_SCHEMA,
                errors=errors,
                description_placeholders={"email": self._reauth_entry.data[CONF_EMAIL]},
            )

        return self.async_update_reload_and_abort(
            self._reauth_entry,
            data_updates={CONF_REFRESH_TOKEN: refresh_token},
        )


class AnioOptionsFlow(OptionsFlow):
    """Configure polling intervals for each reported tracking mode."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage Anio polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NORMAL_INTERVAL,
                    default=options.get(CONF_NORMAL_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _poll_interval_selector(),
                vol.Required(
                    CONF_SCHOOLWAY_INTERVAL,
                    default=options.get(CONF_SCHOOLWAY_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _poll_interval_selector(),
                vol.Required(
                    CONF_EXPLORER_INTERVAL,
                    default=options.get(CONF_EXPLORER_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): _poll_interval_selector(),
                vol.Required(
                    CONF_ACTIVITY_INTERVAL,
                    default=options.get(
                        CONF_ACTIVITY_INTERVAL, DEFAULT_ACTIVITY_INTERVAL_MINUTES
                    ),
                ): _activity_interval_selector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)


class _ValidatedNumberSelector(NumberSelector):
    """Keep number selectors serializable while enforcing server-side validation."""

    def __init__(
        self, config: NumberSelectorConfig, validator: Callable[[Any], int]
    ) -> None:
        super().__init__(config)
        self._validator = validator

    @override
    def __call__(self, value: Any) -> int:
        validated = self._validator(value)
        super().__call__(validated)
        return validated


def _activity_interval_selector() -> NumberSelector:
    """Build the independent activity interval selector in minutes."""
    return _ValidatedNumberSelector(
        NumberSelectorConfig(
            min=MIN_ACTIVITY_INTERVAL_MINUTES,
            max=MAX_ACTIVITY_INTERVAL_MINUTES,
            step=1,
            unit_of_measurement="min",
            mode=NumberSelectorMode.BOX,
        ),
        _validate_activity_interval,
    )


def _validate_activity_interval(value: Any) -> int:
    """Validate an activity interval in whole minutes."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise vol.Invalid("Activity interval must be a whole number of minutes")
    if isinstance(value, float) and not value.is_integer():
        raise vol.Invalid("Activity interval must be a whole number of minutes")
    interval = int(value)
    if not MIN_ACTIVITY_INTERVAL_MINUTES <= interval <= MAX_ACTIVITY_INTERVAL_MINUTES:
        raise vol.Invalid("Activity interval must be between 1 and 1440 minutes")
    return interval


def _poll_interval_selector() -> NumberSelector:
    """Build a bounded numeric selector that accepts only whole-minute values."""
    return _ValidatedNumberSelector(
        NumberSelectorConfig(
            min=MIN_SCAN_INTERVAL,
            max=MAX_SCAN_INTERVAL,
            step=SCAN_INTERVAL_STEP,
            unit_of_measurement="s",
            mode=NumberSelectorMode.BOX,
        ),
        _validate_poll_interval,
    )


def _validate_poll_interval(value: Any) -> int:
    """Reject intervals outside the supported range or not aligned to one minute."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise vol.Invalid("Polling interval must be a whole number of seconds")
    if isinstance(value, float) and not value.is_integer():
        raise vol.Invalid("Polling interval must be a whole number of seconds")
    interval = int(value)
    if (
        interval < MIN_SCAN_INTERVAL
        or interval > MAX_SCAN_INTERVAL
        or interval % SCAN_INTERVAL_STEP
    ):
        raise vol.Invalid("Polling interval must be between 60 and 1800 seconds")
    return interval
