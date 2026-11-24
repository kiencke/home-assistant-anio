"""Tests for Anio polling option validation."""

from types import SimpleNamespace
from unittest.mock import Mock

import probatio
import pytest
from homeassistant.helpers import config_validation as cv

from custom_components.anio.config_flow import (
    AnioOptionsFlow,
    _activity_interval_selector,
    _poll_interval_selector,
)
from custom_components.anio.const import CONF_ACTIVITY_INTERVAL


@pytest.mark.parametrize("interval", [60, 300, 1800])
def test_poll_interval_selector_accepts_supported_values(interval: int) -> None:
    """Whole-minute intervals in the supported range are accepted."""
    assert _poll_interval_selector()(interval) == interval


@pytest.mark.parametrize("interval", [59, 61, 1801, 300.5])
def test_poll_interval_selector_rejects_unsupported_values(
    interval: int | float,
) -> None:
    """Out-of-range or non-minute intervals are rejected."""
    with pytest.raises(probatio.Invalid):
        _poll_interval_selector()(interval)


@pytest.mark.parametrize("interval", [1, 60, 1440])
def test_activity_interval_accepts_whole_minutes(interval: int) -> None:
    """The activity interval includes the default and both bounds."""
    assert _activity_interval_selector()(interval) == interval


@pytest.mark.parametrize("interval", [0, 1441, 1.5, True])
def test_activity_interval_rejects_invalid_values(interval: int | float) -> None:
    """Out-of-range and non-integer activity intervals are rejected."""
    with pytest.raises(probatio.Invalid):
        _activity_interval_selector()(interval)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("options", "expected"), [({}, 60), ({CONF_ACTIVITY_INTERVAL: 17}, 17)]
)
async def test_activity_interval_option_default_and_existing_value(
    options: dict[str, int], expected: int
) -> None:
    """Existing entries gain the default while configured values are retained."""
    flow = AnioOptionsFlow()
    flow.flow_id = "flow"
    flow.handler = "entry-1"
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=Mock(return_value=SimpleNamespace(options=options))
        )
    )
    result = await flow.async_step_init()
    assert result["data_schema"]({})[CONF_ACTIVITY_INTERVAL] == expected
    fields = probatio.to_field_list(
        result["data_schema"], custom_serializer=cv.custom_serializer
    )
    activity = next(
        field for field in fields if field["name"] == CONF_ACTIVITY_INTERVAL
    )
    assert activity["selector"]["number"]["min"] == 1
    assert activity["selector"]["number"]["max"] == 1440
    assert activity["default"] == expected
