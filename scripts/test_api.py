"""Opt-in live smoke tests for the Anio API."""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

from aiohttp import ClientError, ClientSession, ClientTimeout

from custom_components.anio.api import AnioApi, AnioApiError
from custom_components.anio.const import (
    API_BASE_URL,
    API_CLIENT_ID,
    API_LANGUAGE,
    API_USER_AGENT,
)

LIVE_ENV_PATH = Path(__file__).resolve().parents[1] / ".live-test.env"
ACTIVITY_RESPONSE_PATH = LIVE_ENV_PATH.parent / ".live-activity-response"
LIVE_ENV_KEYS = {
    "ANIO_LIVE_TEST",
    "ANIO_EMAIL",
    "ANIO_PASSWORD",
    "ANIO_APP_UUID",
}


def load_live_environment() -> None:
    """Load live-test variables without overriding the process environment."""
    if not LIVE_ENV_PATH.is_file():
        return

    for line_number, raw_line in enumerate(
        LIVE_ENV_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{LIVE_ENV_PATH.name}:{line_number}: expected KEY=VALUE")

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        if key not in LIVE_ENV_KEYS:
            raise ValueError(f"{LIVE_ENV_PATH.name}:{line_number}: unknown key {key}")

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def parse_arguments() -> argparse.Namespace:
    """Read live-test settings and require an explicit opt-in."""
    parser = argparse.ArgumentParser(
        description="Log in to Anio and fetch devices and latest locations."
    )
    try:
        load_live_environment()
    except ValueError as err:
        parser.error(str(err))

    parser.add_argument(
        "--show-devices",
        action="store_true",
        help="Print the full device response, which may contain identifying data.",
    )
    parser.add_argument(
        "--show-locations",
        action="store_true",
        help="Print location data, including exact GPS coordinates.",
    )
    parser.add_argument(
        "--activity",
        action="store_true",
        help="Request /activity and save its unexamined response to a local file.",
    )
    args = parser.parse_args()

    if args.activity and (args.show_devices or args.show_locations):
        parser.error(
            "--activity cannot be combined with --show-devices or --show-locations."
        )
    if os.environ.get("ANIO_LIVE_TEST") != "1":
        parser.error("Live requests require ANIO_LIVE_TEST=1.")

    args.email = os.environ.get("ANIO_EMAIL")
    args.password = os.environ.get("ANIO_PASSWORD")
    if not args.email or not args.password:
        parser.error("Set ANIO_EMAIL and ANIO_PASSWORD in the environment.")

    args.app_uuid = os.environ.get("ANIO_APP_UUID")
    if not args.app_uuid:
        parser.error("Set a fixed ANIO_APP_UUID in .live-test.env.")
    if re.fullmatch(r"[0-9a-fA-F]{16}", args.app_uuid) is None:
        parser.error("ANIO_APP_UUID must contain exactly 16 hexadecimal characters.")
    return args


async def async_run_live_test(args: argparse.Namespace) -> int:
    """Run the selected live test without printing credentials."""
    try:
        async with ClientSession(timeout=ClientTimeout(total=30)) as session:
            api = AnioApi(session, args.app_uuid)
            _, access_token = await api.async_login(args.email, args.password)
            if args.activity:
                return await async_test_activity(session, args.app_uuid, access_token)
            devices = await api.async_get_devices()
            locations = await api.async_get_last_locations()
    except AnioApiError as err:
        print(f"Anio live test failed: {err}", file=sys.stderr)
        return 1

    print("Anio login succeeded.")
    print(f"Device list request succeeded ({len(devices)} device(s)).")
    print(f"Latest locations request succeeded ({len(locations)} record(s)).")
    if args.show_devices:
        print(
            "The following response may contain device identifiers; "
            "do not share it unredacted:",
            file=sys.stderr,
        )
        print(json.dumps(devices, ensure_ascii=False, indent=2))
    if args.show_locations:
        print(
            "The following response contains sensitive location data; "
            "do not share it unredacted:",
            file=sys.stderr,
        )
        print(json.dumps(locations, ensure_ascii=False, indent=2))
    return 0


async def async_test_activity(
    session: ClientSession, app_uuid: str, access_token: str
) -> int:
    """Save the raw activity response and report only its HTTP status."""
    headers = {
        "client-id": API_CLIENT_ID,
        "app-uuid": app_uuid,
        "user-agent": API_USER_AGENT,
        "accept-language": API_LANGUAGE,
        "Authorization": f"Bearer {access_token}",
    }
    try:
        async with session.get(
            f"{API_BASE_URL}/activity", headers=headers, allow_redirects=False
        ) as response:
            print(f"Activity request returned HTTP {response.status}.")
            with ACTIVITY_RESPONSE_PATH.open("xb") as output:
                async for chunk in response.content.iter_chunked(64 * 1024):
                    output.write(chunk)
            print(f"Raw response saved to {ACTIVITY_RESPONSE_PATH}.")
            return 0 if 200 <= response.status < 300 else 1
    except FileExistsError:
        print(
            f"Response file already exists; move it before retrying: "
            f"{ACTIVITY_RESPONSE_PATH}",
            file=sys.stderr,
        )
    except (ClientError, TimeoutError, OSError) as err:
        print(
            f"Activity request or response save failed: {type(err).__name__}",
            file=sys.stderr,
        )
    return 1


def main() -> None:
    """Run the explicitly enabled live smoke test."""
    args = parse_arguments()
    raise SystemExit(asyncio.run(async_run_live_test(args)))


if __name__ == "__main__":
    main()
