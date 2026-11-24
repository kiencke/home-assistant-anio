"""Tests for the live-test environment handling."""

import sys
import uuid
from argparse import Namespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from custom_components.anio.const import API_BASE_URL
from scripts import test_api

TEST_APP_UUID = uuid.uuid4().hex[:16]


def test_live_environment_file_keeps_configured_uuid_and_shell_overrides(
    tmp_path, monkeypatch
) -> None:
    """The env file fills unset variables but never replaces shell values."""
    env_file = tmp_path / ".live-test.env"
    env_file.write_text(
        "ANIO_LIVE_TEST=1\n"
        "ANIO_EMAIL=file@example.com\n"
        "ANIO_PASSWORD='test=pass#word'\n"
        f"ANIO_APP_UUID={TEST_APP_UUID}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(test_api, "LIVE_ENV_PATH", env_file)
    monkeypatch.setenv("ANIO_EMAIL", "shell@example.com")
    monkeypatch.delenv("ANIO_LIVE_TEST", raising=False)
    monkeypatch.delenv("ANIO_PASSWORD", raising=False)
    monkeypatch.delenv("ANIO_APP_UUID", raising=False)
    monkeypatch.setattr(sys, "argv", ["test_api"])

    args = test_api.parse_arguments()

    assert args.email == "shell@example.com"
    assert args.password == "test=pass#word"
    assert args.app_uuid == TEST_APP_UUID


def test_live_test_requires_explicit_opt_in(tmp_path, monkeypatch) -> None:
    """A populated credentials file cannot enable live calls by default."""
    env_file = tmp_path / ".live-test.env"
    env_file.write_text(
        "ANIO_LIVE_TEST=0\n"
        "ANIO_EMAIL=test@example.com\n"
        "ANIO_PASSWORD=dummy\n"
        f"ANIO_APP_UUID={TEST_APP_UUID}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(test_api, "LIVE_ENV_PATH", env_file)
    monkeypatch.delenv("ANIO_LIVE_TEST", raising=False)
    monkeypatch.delenv("ANIO_EMAIL", raising=False)
    monkeypatch.delenv("ANIO_PASSWORD", raising=False)
    monkeypatch.delenv("ANIO_APP_UUID", raising=False)
    monkeypatch.setattr(sys, "argv", ["test_api"])

    with pytest.raises(SystemExit):
        test_api.parse_arguments()


def test_live_test_requires_a_fixed_app_uuid(tmp_path, monkeypatch) -> None:
    """The live test cannot generate a different app UUID for each run."""
    env_file = tmp_path / ".live-test.env"
    env_file.write_text(
        "ANIO_LIVE_TEST=1\nANIO_EMAIL=test@example.com\nANIO_PASSWORD=dummy\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(test_api, "LIVE_ENV_PATH", env_file)
    for key in test_api.LIVE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "argv", ["test_api"])

    with pytest.raises(SystemExit):
        test_api.parse_arguments()


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "exit_code"), [(200, 0), (400, 1), (302, 1)])
async def test_activity_probe_saves_raw_response_without_printing_it(
    tmp_path, monkeypatch, capsys, status: int, exit_code: int
) -> None:
    """The probe reports status and saves bytes without interpreting the body."""
    response_path = tmp_path / ".live-activity-response"
    monkeypatch.setattr(test_api, "ACTIVITY_RESPONSE_PATH", response_path)

    async def chunks(_size: int):
        yield b"private content"
        yield b"\xff"

    response = MagicMock(status=status)
    response.content.iter_chunked = chunks
    session = MagicMock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    result = await test_api.async_test_activity(session, TEST_APP_UUID, "token")

    assert result == exit_code
    assert response_path.read_bytes() == b"private content\xff"
    output = capsys.readouterr()
    assert f"HTTP {status}" in output.out
    assert "private content" not in output.out + output.err
    session.get.assert_called_once()
    assert session.get.call_args.args == (f"{API_BASE_URL}/activity",)
    assert session.get.call_args.kwargs["allow_redirects"] is False
    assert session.get.call_args.kwargs["headers"]["Authorization"] == "Bearer token"


@pytest.mark.asyncio
async def test_activity_probe_does_not_overwrite_existing_response(
    tmp_path, monkeypatch, capsys
) -> None:
    """A previous response remains intact and the conflict is reported."""
    response_path = tmp_path / ".live-activity-response"
    response_path.write_bytes(b"previous")
    monkeypatch.setattr(test_api, "ACTIVITY_RESPONSE_PATH", response_path)
    response = MagicMock(status=200)
    session = MagicMock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    session.get.return_value.__aexit__ = AsyncMock(return_value=None)

    assert await test_api.async_test_activity(session, TEST_APP_UUID, "token") == 1
    assert response_path.read_bytes() == b"previous"
    assert "already exists" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_activity_mode_skips_device_and_location_requests(monkeypatch) -> None:
    """The activity mode performs only login and the requested activity probe."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    api = Mock(
        async_login=AsyncMock(return_value=("refresh", "access")),
        async_get_devices=AsyncMock(),
        async_get_last_locations=AsyncMock(),
    )
    activity = AsyncMock(return_value=0)
    monkeypatch.setattr(test_api, "ClientSession", Mock(return_value=session))
    monkeypatch.setattr(test_api, "AnioApi", Mock(return_value=api))
    monkeypatch.setattr(test_api, "async_test_activity", activity)
    args = Namespace(
        app_uuid=TEST_APP_UUID,
        email="test@example.com",
        password="dummy",
        activity=True,
    )

    assert await test_api.async_run_live_test(args) == 0
    activity.assert_awaited_once_with(session, TEST_APP_UUID, "access")
    api.async_get_devices.assert_not_awaited()
    api.async_get_last_locations.assert_not_awaited()
