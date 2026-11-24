"""Switch platform for Anio watches."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AnioCoordinator
from .entity import get_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up watch control and safety switches."""
    coordinator: AnioCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        entity
        for device in coordinator.devices
        for entity in (
            AnioExplorerSwitch(coordinator, device),
            AnioRadarSwitch(coordinator, device),
            AnioBellProtectionSwitch(coordinator, device),
        )
    )


class AnioExplorerSwitch(CoordinatorEntity[AnioCoordinator], SwitchEntity):
    """Activate or deactivate Explorer tracking on an Anio watch."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radar"
    _attr_translation_key = "explorer"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the Explorer switch."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_explorer"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def is_on(self) -> bool:
        """Return the latest known Explorer state."""
        return self.coordinator.explorer_active(self._device_id) is True

    @property
    @override
    def available(self) -> bool:
        """Require a known state in addition to a successful coordinator update."""
        return (
            super().available
            and self.coordinator.explorer_active(self._device_id) is not None
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate Explorer and use the server-confirmed result."""
        await self.coordinator.async_set_explorer(self._device_id, activate=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Deactivate Explorer and use the server-confirmed result."""
        await self.coordinator.async_set_explorer(self._device_id, activate=False)


class AnioRadarSwitch(CoordinatorEntity[AnioCoordinator], SwitchEntity):
    """Start or stop a time-limited Radar Mode session."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:radar"
    _attr_translation_key = "radar_mode"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the Radar Mode switch."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_radar_mode"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def is_on(self) -> bool:
        """Return whether Radar Mode is active for this watch."""
        return self.coordinator.radar_active(self._device_id)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start Radar Mode after checking the battery guard."""
        await self.coordinator.async_start_radar(self._device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the Radar Mode loop."""
        await self.coordinator.async_stop_radar(self._device_id)


class AnioBellProtectionSwitch(
    CoordinatorEntity[AnioCoordinator], RestoreEntity, SwitchEntity
):
    """Block Find My Device unless the user deliberately disables protection."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:bell-lock-outline"
    _attr_translation_key = "bell_protection"

    def __init__(self, coordinator: AnioCoordinator, device: dict[str, Any]) -> None:
        """Initialize the Find My Device safety switch."""
        super().__init__(coordinator)
        self._device_id = device["id"].strip()
        self._attr_unique_id = f"{self._device_id}_bell_protection"
        self._attr_device_info = get_device_info(device)

    @property
    @override
    def is_on(self) -> bool:
        """Return whether Find My Device remains blocked."""
        return self.coordinator.bell_protection_enabled(self._device_id)

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the safety setting; first-time installs stay protected."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is None:
            return
        if last_state.state not in (STATE_ON, STATE_OFF):
            return
        self.coordinator.set_bell_protection(
            self._device_id, last_state.state == STATE_ON
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the default-on protection."""
        self.coordinator.set_bell_protection(self._device_id, True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Allow the user to deliberately enable Find My Device."""
        self.coordinator.set_bell_protection(self._device_id, False)
        self.async_write_ha_state()
