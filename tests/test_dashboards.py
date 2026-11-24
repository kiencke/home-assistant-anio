"""Tests for the example watch dashboards."""

from pathlib import Path

import pytest
import yaml

EXAMPLES = Path(__file__).parents[1] / "examples" / "dashboards"


@pytest.mark.parametrize(
    ("language", "headings"),
    [
        ("en", ["Location", "Chat", "More Functions"]),
        ("de", ["Standort", "Chat", "Weitere Funktionen"]),
    ],
)
def test_watch_dashboard_layout(language: str, headings: list[str]) -> None:
    """The examples use the requested native grid layout and working actions."""
    data = yaml.safe_load(
        (EXAMPLES / f"watch_dashboard_{language}.yaml").read_text(encoding="utf-8")
    )
    view = data["views"][0]
    assert view["type"] == "sections"
    assert view["max_columns"] == 3
    assert [badge["entity"] for badge in view["badges"]] == [
        "sensor.<device_slug>_network_quality",
        "sensor.<device_slug>_position_source",
        "sensor.<device_slug>_gps_accuracy",
        "sensor.<device_slug>_battery",
    ]
    assert all(
        badge["type"] == "entity"
        and not badge["show_name"]
        and badge["show_state"]
        and badge["show_icon"]
        for badge in view["badges"]
    )
    sections = view["sections"]
    assert len(sections) == 3
    for section, heading in zip(sections, headings, strict=True):
        assert section["type"] == "grid"
        assert section["cards"][0] == {
            "type": "heading",
            "heading_style": "title",
            "heading": heading,
        }

    location = sections[0]["cards"][1:]
    assert [card["type"] for card in location] == [
        "map",
        "button",
        "tile",
        "tile",
        "tile",
        "tile",
        "tile",
        "tile",
    ]
    assert location[0]["grid_options"]["columns"] == "full"
    assert location[0]["theme_mode"] == "auto"
    assert location[0]["entities"][0]["color"] == "indigo"
    assert location[0]["entities"][0]["label_mode"] == "icon"
    assert location[1]["grid_options"] == {"columns": 6, "rows": 2}
    assert "name" not in location[2]
    assert all(card["grid_options"]["columns"] == 6 for card in location[1:])
    assert all(card["vertical"] is False for card in location[2:])
    assert sections[1]["cards"][1]["type"] == "custom:anio-chat-card"
    assert sections[1]["cards"][1]["device_id"] == "<ha_device_id>"
    ring, protection = sections[2]["cards"][1:]
    assert ring["hide_state"] and ring["vertical"] and protection["vertical"]
    assert protection["icon"] == "mdi:shield-lock"
    assert protection["features"] == [{"type": "toggle"}]
    assert protection["features_position"] == "bottom"
    for card, action_name in [
        (location[1], "tap_action"),
        (ring, "tap_action"),
        (ring, "icon_tap_action"),
    ]:
        action = card[action_name]
        assert action["action"] == "perform-action"
        assert action["perform_action"] == "button.press"
        assert action["target"]["entity_id"] == card["entity"]


def test_dashboard_locales_use_identical_entities() -> None:
    """Only section titles differ between the German and English views."""
    views = [
        yaml.safe_load(
            (EXAMPLES / f"watch_dashboard_{language}.yaml").read_text(
                encoding="utf-8"
            )
        )
        for language in ("en", "de")
    ]
    for view in views:
        for section in view["views"][0]["sections"]:
            section["cards"][0].pop("heading")
    assert views[0] == views[1]


def test_dashboard_cards_use_entity_names() -> None:
    """Entity card names are not overridden with fixed text."""
    for path in EXAMPLES.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))

        def check(value: object) -> None:
            if isinstance(value, dict):
                if "type" in value and "name" in value:
                    assert value["name"] == {"type": "entity"}, path
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(data)


def test_native_fallback_uses_same_message_sensor() -> None:
    """The fallback displays history from the same entity as its entity card."""
    fallback = yaml.safe_load(
        (EXAMPLES / "native_chat_fallback.yaml").read_text(encoding="utf-8")
    )
    entity_id = fallback["cards"][0]["entities"][1]["entity"]
    assert entity_id in fallback["cards"][1]["content"]
