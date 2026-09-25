"""Tests for the Concept2 Logbook sensor platform."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2Result
from custom_components.concept2.const import DOMAIN

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"

SENSOR_KEYS = [
    "last_workout_date",
    "last_workout_distance",
    "last_workout_duration",
    "days_since_last_workout",
]


def _make_result(date: datetime) -> Concept2Result:
    return Concept2Result(
        result_id=1,
        date=date,
        distance_meters=6000,
        duration_seconds=1350.0,
        calories_total=450,
        stroke_count=900,
        stroke_rate=24,
        drag_factor=128,
    )


async def _setup_entry(hass: HomeAssistant, mock_config_entry, result) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch(RESULT_PATH, AsyncMock(return_value=result)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, mock_config_entry, key: str) -> str:
    registry = er.async_get(hass)
    unique_id = f"concept2_{mock_config_entry.unique_id}_{key}"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


def _last_workout_date_entity_id(hass: HomeAssistant, mock_config_entry) -> str:
    return _entity_id(hass, mock_config_entry, "last_workout_date")


async def test_last_workout_date_populated(hass: HomeAssistant, mock_config_entry) -> None:
    """The sensor reports the most recent rower result's timestamp."""
    workout_date = dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0))
    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    entity_id = _last_workout_date_entity_id(hass, mock_config_entry)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == workout_date.isoformat()


async def test_last_workout_date_unknown_with_no_results(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The sensor reports unknown when there are no rower results yet."""
    await _setup_entry(hass, mock_config_entry, None)

    entity_id = _last_workout_date_entity_id(hass, mock_config_entry)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNKNOWN


async def test_all_sensors_unknown_with_no_results(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """All four sensors report unknown when zero rower results exist."""
    await _setup_entry(hass, mock_config_entry, None)

    for key in SENSOR_KEYS:
        entity_id = _entity_id(hass, mock_config_entry, key)
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN, f"{key} should be unknown"


async def test_last_workout_date_extra_attributes(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """calories_total, stroke_count, stroke_rate, and drag_factor attach to last_workout_date."""
    workout_date = dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0))
    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    entity_id = _last_workout_date_entity_id(hass, mock_config_entry)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["calories_total"] == 450
    assert state.attributes["stroke_count"] == 900
    assert state.attributes["stroke_rate"] == 24
    assert state.attributes["drag_factor"] == 128


async def test_last_workout_distance_and_duration_populated(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Distance and duration sensors report correct values, units, and device classes."""
    workout_date = dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0))
    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    distance_id = _entity_id(hass, mock_config_entry, "last_workout_distance")
    distance_state = hass.states.get(distance_id)
    assert distance_state is not None
    assert distance_state.state == "6000"
    assert distance_state.attributes["unit_of_measurement"] == "m"
    assert distance_state.attributes["device_class"] == "distance"
    assert distance_state.attributes["state_class"] == "measurement"

    duration_id = _entity_id(hass, mock_config_entry, "last_workout_duration")
    duration_state = hass.states.get(duration_id)
    assert duration_state is not None
    assert duration_state.state == "1350.0"
    assert duration_state.attributes["unit_of_measurement"] == "s"
    assert duration_state.attributes["device_class"] == "duration"
    assert duration_state.attributes["state_class"] == "measurement"


async def test_days_since_last_workout_same_day(
    hass: HomeAssistant, mock_config_entry, freezer
) -> None:
    """A workout logged today (local time) reports 0 days since."""
    hass.config.set_time_zone("America/Los_Angeles")
    freezer.move_to("2026-09-15 18:00:00-07:00")

    workout_date = datetime(2026, 9, 15, 8, 0, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    entity_id = _entity_id(hass, mock_config_entry, "days_since_last_workout")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "0"
    assert state.attributes["unit_of_measurement"] == "d"
    assert state.attributes["state_class"] == "measurement"


async def test_days_since_last_workout_late_night_local_boundary(
    hass: HomeAssistant, mock_config_entry, freezer
) -> None:
    """A late-night local workout isn't miscounted due to UTC day rollover.

    A row finished at 23:45 local time on Sep 15 is already Sep 16 in UTC. If the
    day-diff math used UTC dates instead of local ones, "now" a few minutes later
    (still Sep 15 local, Sep 16 UTC) would wrongly report 1 day since instead of 0.
    """
    hass.config.set_time_zone("America/Los_Angeles")
    workout_date = datetime(2026, 9, 15, 23, 45, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    freezer.move_to(workout_date + timedelta(minutes=10))

    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    entity_id = _entity_id(hass, mock_config_entry, "days_since_last_workout")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "0"


async def test_days_since_last_workout_midnight_boundary(
    hass: HomeAssistant, mock_config_entry, freezer
) -> None:
    """A workout the previous local calendar day reports 1, once local midnight has passed."""
    hass.config.set_time_zone("America/Los_Angeles")
    workout_date = datetime(2026, 9, 15, 23, 45, 0, tzinfo=dt_util.DEFAULT_TIME_ZONE)
    freezer.move_to("2026-09-16 00:15:00-07:00")

    result = _make_result(workout_date)
    await _setup_entry(hass, mock_config_entry, result)

    entity_id = _entity_id(hass, mock_config_entry, "days_since_last_workout")
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "1"
