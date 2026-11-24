# Anio for Home Assistant

[Deutsch](README.de.md) | English

An unofficial Home Assistant integration for Anio children's watches. Connect
an Anio cloud account to see watches as devices, display their location and
activities, and exchange text messages.

> **Important:** This is an independent hobby project, not affiliated with or
> supported by ANIO GmbH. Location data may be delayed or inaccurate. Do not
> rely on this integration as a safety or emergency system.

## What it can do

- Show a watch's last reported location, battery and diagnostic information.
- Request a new location, control Explorer mode and use a time-limited Radar
  Mode. Ringing the watch requires deliberately disabling bell protection.
- Send text and emojis and view chat history on supported watches.
- Show Anio watch activities, including Anio geofence events, in a dashboard.
- Add bundled location, chat and activity cards to a dashboard.

Watch features depend on the device and its Anio configuration. Voice messages
cannot currently be played or sent, even if a recording control is visible.
See [Limitations](#limitations) before use.

## Requirements

- A running Home Assistant installation with Marketplace (Home Assistant
  2026.11 or newer) or HACS (older versions).
- An Anio cloud account with at least one linked watch and an internet
  connection from Home Assistant to the Anio cloud.
- A compatible Home Assistant version. The minimum supported version has not
  yet been established; installation and setup still need validation on a
  clean Home Assistant instance.

## Installation via Marketplace / HACS

### Marketplace (Home Assistant 2026.11 or newer)

1. Open **Settings > Marketplace** and select **Add from link**.
2. Enter `https://github.com/kiencke/home-assistant-anio` and add it. Connect
   GitHub if requested and select **Integration** if prompted for a type.
3. Open **Anio** and select **Install**.
4. Restart Home Assistant.

### HACS (older Home Assistant versions)

1. Open HACS and choose **Custom repositories** from the three-dot menu.
2. Enter `https://github.com/kiencke/home-assistant-anio`, select
   **Integration** as the type and add the repository.
3. Open **Anio** in HACS and download it.
4. Restart Home Assistant.

See the [Marketplace guide](https://www.home-assistant.io/integrations/marketplace/#custom-repositories)
or [HACS guide](https://www.hacs.xyz/docs/faq/custom_repositories/) for details.
These installation paths have not yet been validated for this project.

## Connect your Anio account

1. In Home Assistant, open **Settings > Devices & services > Add integration**.
2. Search for **Anio (Unofficial)** and enter the email address and password
   used for your Anio account.
3. Keep the suggested App UUID, or leave it empty to generate one. A custom
   value must contain exactly 16 hexadecimal characters.
4. Finish setup. Home Assistant creates a device for each watch returned by
   the account.

If Home Assistant requests reauthentication later, enter your Anio password
again. Setup requires a successful initial location fetch; a cloud or location
error can prevent setup even if sign-in succeeds.

## Dashboard and controls

In dashboard edit mode, add an **Anio location**, **Anio chat**, or **Anio
activities** card and select a watch. The cards are registered automatically;
no separate dashboard resource is needed. Chat controls appear only for
supported devices. If a card is not found after installation, reload the
browser after restarting Home Assistant.

The [dashboard examples](examples/dashboards) include English and German
sections views. Copy a view into your dashboard's raw configuration, replace
`<device_slug>` and `<ha_device_id>`, and check each entity ID in **Settings >
Devices & services > Entities**. Entity IDs can differ with language or prior
customization. To find the device registry ID, select the watch in the chat
card editor and inspect its YAML configuration.

The location card shows the time of the last position update. An old position
is not necessarily the watch's current position. **Request location** asks the
watch for a new fix; the status changes to updated only when a newer position
timestamp is received.

Radar Mode repeatedly requests a location for a limited time. It defaults to
15 minutes with a 90-second interval and requires a known battery level of at
least 20%; it stops on low or unknown battery, API rate limiting or timeout.
To ring the watch, first turn off **Bell protection**. Quiet hours and school
mode are not automatically detected for ringing.

## Polling and activities

Use the integration's **Configure** option to change polling intervals:

| Data | Default | Allowed |
| --- | --- | --- |
| Location: Normal and Schoolway | 300 seconds | 60–1800 seconds, in 60-second steps |
| Location: Explorer | 60 seconds | 60–1800 seconds, in 60-second steps |
| Activities | 60 minutes | 1–1440 minutes |

These settings control Home Assistant's cloud requests, not the watch's own
location interval. The shortest configured interval for the reported watch
modes is used for the shared location endpoint.

The visible chat card refreshes every 30 seconds; chat is also fetched after
successful location requests and after sending. Activities are fetched at
startup, periodically, when the activity card becomes visible, and with its
refresh button. Automatic card openings are limited to one activity request
per 30 seconds; the button bypasses this cooldown.

**Anio zones** are configured in the Anio system and are not Home Assistant
zones. For display and sorting, departure times are rounded to whole seconds
and estimated one minute earlier. This can reorder unrelated events; the
original timestamp remains in the activity sensor. Server-side history limits
and paging are not known, so earlier or missed activities may be unavailable.

## Privacy

Home Assistant stores the account email address, App UUID and refresh token;
the password and access token are not stored in the config entry. Protect your
Home Assistant backups and configuration directory.

Chat history and activities are stored locally. Chat messages, activity text,
zone names and timestamps may be visible in entity attributes. Message
contents may also appear in events and be stored by Home Assistant's Recorder.
The activity list is excluded from Recorder, but may be accessible to other
integrations and users with access to entity states. Stored histories and
entity state size grow over time.

Text messages use the triggering Home Assistant user's display name as their
Anio sender when available, otherwise `HA`; this name is sent to the Anio
cloud. Emoji messages use `HA`. Never publish credentials, tokens, raw API
responses, personal messages or precise locations in issues or screenshots.

## Limitations

- The integration uses an unofficial cloud API and may stop working if it
  changes. Availability and compatibility with all watch models are unverified.
- Position timestamps and network responses are distinct; a recent response
  does not necessarily mean a recent position. GPS accuracy is interpreted as
  meters, but its API unit is not verified. Speed and direction are raw values.
- Voice-message playback and sending are not implemented. Emoji mapping is
  inferred from the app and has not been fully verified.
- Activities are deduplicated by activity ID. Separate duplicate geofence
  events from the cloud can still appear.

## Development and license

See the [development guide](docs/development.md) for tests, API notes and the
opt-in live smoke test. Licensed under the [MIT License](LICENSE).
