"""Tests for the Concept2 Logbook sensor platform."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2Result
from custom_components.concept2.const import DOMAIN

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"


async def _setup_entry(hass: HomeAssistant, mock_config_entry, result) -> None:
    mock_config_entry.add_to_hass(hass)
    with patch(RESULT_PATH, AsyncMock(return_value=result)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


def _last_workout_date_entity_id(hass: HomeAssistant, mock_config_entry) -> str:
    registry = er.async_get(hass)
    unique_id = f"concept2_{mock_config_entry.unique_id}_last_workout_date"
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


async def test_last_workout_date_populated(hass: HomeAssistant, mock_config_entry) -> None:
    """The sensor reports the most recent rower result's timestamp."""
    workout_date = dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0))
    result = Concept2Result(
        result_id=1,
        date=workout_date,
        distance_meters=6000,
        duration_seconds=1350.0,
        calories_total=450,
        stroke_count=900,
        stroke_rate=24,
        drag_factor=128,
    )
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
