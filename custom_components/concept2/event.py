"""Event platform for the Concept2 Logbook integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import Concept2Result, pace_500m_seconds
from .const import EVENT_TYPE_WORKOUT_LOGGED
from .coordinator import Concept2DataUpdateCoordinator
from .entity import Concept2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Concept2 Logbook new-workout event entity from a config entry."""
    coordinator: Concept2DataUpdateCoordinator = entry.runtime_data
    async_add_entities([Concept2NewWorkoutEvent(coordinator, entry)])


class Concept2NewWorkoutEvent(Concept2Entity, EventEntity):
    """Fires `workout_logged` once per newly logged rower result, oldest first."""

    _attr_translation_key = "new_workout"
    _attr_event_types = [EVENT_TYPE_WORKOUT_LOGGED]

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_new_workout"

    async def async_added_to_hass(self) -> None:
        """Register for future updates, then catch up on the refresh that already ran.

        `async_config_entry_first_refresh` completes before platforms are set up, so a
        result that's new at HA startup would otherwise never reach a listener.
        """
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Fire one event per newly detected result, oldest first."""
        for result in self.coordinator.data.new_results:
            self._trigger_event(EVENT_TYPE_WORKOUT_LOGGED, _event_attributes(result))
            self.async_write_ha_state()


def _event_attributes(result: Concept2Result) -> dict[str, Any]:
    """Build the workout_logged event payload from a result."""
    return {
        "result_id": result.result_id,
        "date": result.date.isoformat(),
        "distance_meters": result.distance_meters,
        "duration_seconds": result.duration_seconds,
        "pace_500m_seconds": pace_500m_seconds(result),
        "calories_total": result.calories_total,
        "stroke_count": result.stroke_count,
        "stroke_rate": result.stroke_rate,
        "drag_factor": result.drag_factor,
        "heart_rate_avg": result.heart_rate_avg,
        "heart_rate_ending": result.heart_rate_ending,
    }
