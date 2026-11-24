# Development

[English user guide](../README.md) | [Deutsche Anleitung](../README.de.md)

## Setup

Development requires Python 3.13 or newer and Git. Node.js is needed for the
dashboard card tests. Docker is optional for testing a Home Assistant instance.
The minimum supported Home Assistant version has not yet been established.

Example on Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the linter and offline tests:

```powershell
ruff check .
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest -p pytest_asyncio.plugin tests --ignore=tests\test_config_flow.py
node --test tests\test_chat_card.cjs
```

The Home Assistant test plugin imports Unix-specific modules on Windows.
Run `tests/test_config_flow.py` in a supported Linux environment with the
Home Assistant test plugin installed. The regular pytest suite uses mocked
responses and does not contact the Anio cloud.

## Live smoke test

Live calls are opt-in. Copy `.live-test.env.example` to `.live-test.env`, fill
in your credentials and a private, fixed 16-character hexadecimal
`ANIO_APP_UUID`, and set `ANIO_LIVE_TEST=1` only when ready. The local
`.live-test.env` is ignored by Git and is not included in a clone.

```powershell
Copy-Item .live-test.env.example .live-test.env
notepad .live-test.env
.\.venv\Scripts\python.exe -c "import uuid; print(uuid.uuid4().hex[:16])"
.\.venv\Scripts\python.exe -m scripts.test_api
.\.venv\Scripts\python.exe -m scripts.test_api --show-locations
```

Generate the App UUID once and keep it unchanged for future runs to avoid
repeated app notifications. Environment variables already set in PowerShell
take precedence over values in `.live-test.env`.

Probe the activity endpoint separately:

```powershell
.\.venv\Scripts\python.exe -m scripts.test_api --activity
```

After login, this makes one `GET /v1/activity` without query parameters, prints
the HTTP status, and saves the raw response to `.live-activity-response`
without printing or inspecting it. The ignored file may contain sensitive
data: inspect and redact it yourself before sharing. The script never
overwrites an existing response file; move or remove it before another probe.
Non-2xx responses are also saved and cause a nonzero exit.

`--show-devices` prints the full device response, including possible device
identifiers. `--show-locations` prints the full location response, including
precise GPS coordinates. Do not share either output without redacting it. The
script does not print credentials or tokens.

## Implementation notes

- The location endpoint returns records matched only by `deviceId`. The
  reported `trackingMode` determines the location polling interval; whether
  the API updates it immediately after a mode change is not yet known.
- `date` belongs to the location record. The exact meaning of `lastResponse`
  is unverified and it may change without a new fix. `signalStrength` is a
  percentage. GPS accuracy is interpreted as meters by request, but the API
  unit is unverified; speed and direction are raw values.
- Location, chat and activity requests share an API lock. The regular chat
  poll runs in a background task after a successful location fetch. Chat
  refreshes and activity refreshes notify entities without resetting the
  location timer. Activity polling has its own schedule.
- Activities are stored in private Home Assistant storage and deduplicated by
  ID. No Home Assistant events are fired for activities. On polling or save
  failure, the activity card warns while retaining history; saving is retried
  after a later successful poll. Server-side history limits and paging remain
  unknown.
- Authenticated audio endpoints deliberately return `501 Not Implemented`:
  the audio API and codec have not been verified.

Do not commit credentials, raw API responses, personal messages or precise
locations. The local `doc/` contents and live response files are Git-ignored;
public documentation belongs in `docs/`.
