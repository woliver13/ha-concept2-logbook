"""Button platform for the Concept2 Logbook integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import Concept2DataUpdateCoordinator
from .entity import Concept2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Concept2 Logbook refresh button from a config entry."""
    coordinator: Concept2DataUpdateCoordinator = entry.runtime_data
    async_add_entities([Concept2RefreshButton(coordinator, entry)])


class Concept2RefreshButton(Concept2Entity, ButtonEntity):
    """Fetches the latest logged rowing result on demand, outside the nightly schedule."""

    _attr_translation_key = "refresh"

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_refresh"

    async def async_press(self) -> None:
        """Refresh the coordinator immediately."""
        await self.coordinator.async_request_refresh()
