"""Sensor platform for the Concept2 Logbook integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER
from .coordinator import Concept2DataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Concept2 Logbook sensors from a config entry."""
    coordinator: Concept2DataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        [
            Concept2LastWorkoutDateSensor(coordinator, entry),
            Concept2LastWorkoutDistanceSensor(coordinator, entry),
            Concept2LastWorkoutDurationSensor(coordinator, entry),
            Concept2DaysSinceLastWorkoutSensor(coordinator, entry),
        ]
    )


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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra API fields not worth a dedicated sensor of their own."""
        result = self.coordinator.data
        if result is None:
            return None
        return {
            "calories_total": result.calories_total,
            "stroke_count": result.stroke_count,
            "stroke_rate": result.stroke_rate,
            "drag_factor": result.drag_factor,
        }


class Concept2LastWorkoutDistanceSensor(Concept2Entity, SensorEntity):
    """Distance of the most recently logged rowing result."""

    _attr_translation_key = "last_workout_distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfLength.METERS

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_last_workout_distance"

    @property
    def native_value(self) -> float | None:
        """Return the most recent rower result's distance, or None if there isn't one."""
        result = self.coordinator.data
        return result.distance_meters if result is not None else None


class Concept2LastWorkoutDurationSensor(Concept2Entity, SensorEntity):
    """Duration of the most recently logged rowing result."""

    _attr_translation_key = "last_workout_duration"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_last_workout_duration"

    @property
    def native_value(self) -> float | None:
        """Return the most recent rower result's duration, or None if there isn't one."""
        result = self.coordinator.data
        return result.duration_seconds if result is not None else None


class Concept2DaysSinceLastWorkoutSensor(Concept2Entity, SensorEntity):
    """Number of calendar days since the most recently logged rowing result."""

    _attr_translation_key = "days_since_last_workout"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(
        self, coordinator: Concept2DataUpdateCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"concept2_{entry.unique_id}_days_since_last_workout"

    @property
    def native_value(self) -> int | None:
        """Return the calendar-day gap since the last rower result, or None if there isn't one.

        The workout timestamp is converted to HA's configured local timezone before
        computing the calendar-day difference from "now", so a row finished late at
        night in local time isn't miscounted due to UTC rollover.
        """
        result = self.coordinator.data
        if result is None:
            return None
        last_workout_date = dt_util.as_local(result.date).date()
        today = dt_util.now().date()
        return (today - last_workout_date).days
