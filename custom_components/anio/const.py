"""Constants for the Anio integration."""

from homeassistant.const import Platform

DOMAIN = "anio"
EVENT_CHAT_MESSAGE_RECEIVED = "anio_chat_message_received"
CHAT_USERNAME = "HA"
SERVICE_SEND_EMOJI = "send_emoji"
SERVICE_REFRESH_CHAT = "refresh_chat"
SERVICE_REFRESH_ACTIVITIES = "refresh_activities"
ANIO_EMOJIS: dict[str, dict[str, str]] = {
    "E01": {
        "emoji": "🙂",
        "name": "smile",
        "icon": "mdi:emoticon-happy-outline",
    },
    "E02": {
        "emoji": "😘",
        "name": "kiss",
        "icon": "mdi:emoticon-kiss-outline",
    },
    "E03": {
        "emoji": "😎",
        "name": "cool",
        "icon": "mdi:emoticon-cool-outline",
    },
    "E04": {
        "emoji": "🙁",
        "name": "sad",
        "icon": "mdi:emoticon-sad-outline",
    },
    "E05": {
        "emoji": "😁",
        "name": "grin",
        "icon": "mdi:emoticon-excited-outline",
    },
    "E06": {
        "emoji": "😛",
        "name": "tongue",
        "icon": "mdi:emoticon-tongue-outline",
    },
    "E07": {
        "emoji": "👎",
        "name": "thumbs_down",
        "icon": "mdi:thumb-down-outline",
    },
    "E08": {
        "emoji": "👍",
        "name": "thumbs_up",
        "icon": "mdi:thumb-up-outline",
    },
    "E09": {
        "emoji": "❤️",
        "name": "heart",
        "icon": "mdi:heart",
    },
}
API_BASE_URL = "https://api.anio.cloud/v1"
API_CLIENT_ID = "ANIO"
API_USER_AGENT = (
    "Anio/3.4.2 (com.anio.watch;build:20260925;Android 37;Google;sdk_gphone64_x86_64)"
)
API_LANGUAGE = "de"

CONF_APP_UUID = "app_uuid"
CONF_REFRESH_TOKEN = "refresh_token"

DEFAULT_SCAN_INTERVAL = 300
DEFAULT_EXPLORER_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 1800
SCAN_INTERVAL_STEP = 60
RADAR_DEFAULT_DURATION_MINUTES = 15
RADAR_MIN_DURATION_MINUTES = 5
RADAR_MAX_DURATION_MINUTES = 20
RADAR_DEFAULT_INTERVAL_SECONDS = 90
RADAR_MIN_INTERVAL_SECONDS = 60
RADAR_MAX_INTERVAL_SECONDS = 1800
RADAR_LOCATION_WAIT_SECONDS = 5
RADAR_MIN_BATTERY_PERCENT = 20
CONF_NORMAL_INTERVAL = "normal_interval"
CONF_SCHOOLWAY_INTERVAL = "schoolway_interval"
CONF_EXPLORER_INTERVAL = "explorer_interval"
CONF_ACTIVITY_INTERVAL = "activity_interval"
DEFAULT_ACTIVITY_INTERVAL_MINUTES = 60
MIN_ACTIVITY_INTERVAL_MINUTES = 1
MAX_ACTIVITY_INTERVAL_MINUTES = 1440
TRACKING_MODES = {
    "NORMAL": CONF_NORMAL_INTERVAL,
    "SCHOOLWAY": CONF_SCHOOLWAY_INTERVAL,
    "EXPLORER": CONF_EXPLORER_INTERVAL,
}
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.NUMBER,
    Platform.NOTIFY,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]
