"""Sensor platform for the Concept2 Logbook integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import Concept2DataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Concept2 Logbook sensors from a config entry."""
    coordinator: Concept2DataUpdateCoordinator = entry.runtime_data
    async_add_entities([Concept2LastWorkoutDateSensor(coordinator, entry)])


class Concept2Entity(CoordinatorEntity[Concept2DataUpdateCoordinator]):
    """Base entity tying a Concept2 sensor to its account's device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the entity and its shared device info."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name="Concept2 Logbook",
            manufacturer=MANUFACTURER,
        )


class Concept2LastWorkoutDateSensor(Concept2Entity, SensorEntity):
    """Timestamp of the most recently logged rowing result."""

    _attr_translation_key = "last_workout_date"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_last_workout_date"

    @property
    def native_value(self) -> datetime | None:
        """Return the most recent rower result's timestamp, or None if there isn't one."""
        result = self.coordinator.data
        return result.date if result is not None else None
