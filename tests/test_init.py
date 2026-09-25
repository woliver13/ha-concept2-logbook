"""Tests for the Concept2 Logbook integration setup and nightly refresh schedule."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2Result

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"

RESULT = Concept2Result(
    result_id=1,
    date=dt_util.as_utc(datetime(2026, 9, 15, 8, 0, 0)),
    distance_meters=6000,
    duration_seconds=1350.0,
    calories_total=450,
    stroke_count=900,
    stroke_rate=24,
    drag_factor=128,
)


async def _advance_to(hass: HomeAssistant, freezer: FrozenDateTimeFactory, when: datetime) -> None:
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


async def test_nightly_refresh_fires_at_local_3am(
    hass: HomeAssistant, mock_config_entry, freezer: FrozenDateTimeFactory
) -> None:
    """The nightly trigger refreshes at 3:00 AM in HA's local timezone, not 3:00 AM UTC."""
    hass.config.set_time_zone("America/Los_Angeles")
    local_tz = dt_util.DEFAULT_TIME_ZONE
    freezer.move_to(datetime(2026, 9, 20, 18, 0, 0, tzinfo=local_tz))

    mock_config_entry.add_to_hass(hass)
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_fetch.call_count == 1

        # 3:00 AM UTC is 8:00 PM the previous evening in Los Angeles — no refresh.
        await _advance_to(hass, freezer, datetime(2026, 9, 21, 3, 0, 0, tzinfo=dt_util.UTC))
        assert mock_fetch.call_count == 1

        await _advance_to(hass, freezer, datetime(2026, 9, 21, 2, 59, 59, tzinfo=local_tz))
        assert mock_fetch.call_count == 1

        await _advance_to(hass, freezer, datetime(2026, 9, 21, 3, 0, 0, tzinfo=local_tz))
        assert mock_fetch.call_count == 2

        # And again the following night.
        await _advance_to(hass, freezer, datetime(2026, 9, 22, 3, 0, 0, tzinfo=local_tz))
        assert mock_fetch.call_count == 3


async def test_nightly_refresh_stops_after_unload(
    hass: HomeAssistant, mock_config_entry, freezer: FrozenDateTimeFactory
) -> None:
    """Unloading the entry cancels the nightly trigger."""
    hass.config.set_time_zone("America/Los_Angeles")
    local_tz = dt_util.DEFAULT_TIME_ZONE
    freezer.move_to(datetime(2026, 9, 20, 18, 0, 0, tzinfo=local_tz))

    mock_config_entry.add_to_hass(hass)
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await _advance_to(hass, freezer, datetime(2026, 9, 21, 3, 0, 0, tzinfo=local_tz))

    assert mock_fetch.call_count == 1
