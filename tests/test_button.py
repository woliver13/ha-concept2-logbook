"""Tests for the Concept2 Logbook refresh button."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2Result
from custom_components.concept2.const import DOMAIN

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"


def _make_result(distance_meters: int) -> Concept2Result:
    return Concept2Result(
        result_id=1,
        date=dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0)),
        distance_meters=distance_meters,
        duration_seconds=1350.0,
        calories_total=450,
        stroke_count=900,
        stroke_rate=24,
        drag_factor=128,
    )


def _entity_id(hass: HomeAssistant, mock_config_entry, platform: str, key: str) -> str:
    registry = er.async_get(hass)
    unique_id = f"concept2_{mock_config_entry.unique_id}_{key}"
    entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


async def test_refresh_button_triggers_immediate_refresh(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Pressing the refresh button fetches from the API again and updates the sensors."""
    mock_config_entry.add_to_hass(hass)
    mock_fetch = AsyncMock(return_value=_make_result(6000))
    with patch(RESULT_PATH, mock_fetch):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_fetch.call_count == 1

        mock_fetch.return_value = _make_result(7500)
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: _entity_id(hass, mock_config_entry, "button", "refresh")},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert mock_fetch.call_count == 2
    distance = hass.states.get(
        _entity_id(hass, mock_config_entry, "sensor", "last_workout_distance")
    )
    assert float(distance.state) == 7500
