"""Tests for non-auth poll failure handling and the repair issue."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2ConnectionError, Concept2Result
from custom_components.concept2.const import DOMAIN

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


def _issue(hass: HomeAssistant, mock_config_entry) -> ir.IssueEntry | None:
    return ir.async_get(hass).async_get_issue(
        DOMAIN, f"poll_failing_{mock_config_entry.entry_id}"
    )


def _distance_state(hass: HomeAssistant, mock_config_entry):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"concept2_{mock_config_entry.unique_id}_last_workout_distance"
    )
    assert entity_id is not None
    return hass.states.get(entity_id)


async def _set_up(hass: HomeAssistant, mock_config_entry, mock_fetch: AsyncMock):
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry.runtime_data


async def test_single_failed_poll_raises_update_failed_and_keeps_values(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """One failed poll raises UpdateFailed but the sensors keep their last values."""
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        coordinator = await _set_up(hass, mock_config_entry, mock_fetch)

        mock_fetch.side_effect = Concept2ConnectionError("boom")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        await coordinator.async_refresh()
        await hass.async_block_till_done()

    assert coordinator.last_update_success is False
    assert coordinator.data == RESULT
    state = _distance_state(hass, mock_config_entry)
    assert state.state == "6000"


async def test_fewer_than_three_failures_create_no_repair_issue(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Two consecutive failures do not raise a repair issue."""
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        coordinator = await _set_up(hass, mock_config_entry, mock_fetch)

        mock_fetch.side_effect = Concept2ConnectionError("boom")
        await coordinator.async_refresh()
        await coordinator.async_refresh()

    assert _issue(hass, mock_config_entry) is None


async def test_third_consecutive_failure_creates_repair_issue(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The third failure in a row raises exactly one repair issue, and later ones keep it."""
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        coordinator = await _set_up(hass, mock_config_entry, mock_fetch)

        mock_fetch.side_effect = Concept2ConnectionError("boom")
        for _ in range(3):
            await coordinator.async_refresh()

        issue = _issue(hass, mock_config_entry)
        assert issue is not None
        assert issue.severity == ir.IssueSeverity.WARNING
        assert issue.is_fixable is False

        await coordinator.async_refresh()

    assert _issue(hass, mock_config_entry) is not None
    assert len(ir.async_get(hass).issues) == 1


async def test_success_clears_repair_issue_and_resets_counter(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A successful poll clears the issue and restarts the count from zero."""
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        coordinator = await _set_up(hass, mock_config_entry, mock_fetch)

        mock_fetch.side_effect = Concept2ConnectionError("boom")
        for _ in range(3):
            await coordinator.async_refresh()
        assert _issue(hass, mock_config_entry) is not None

        mock_fetch.side_effect = None
        mock_fetch.return_value = RESULT
        await coordinator.async_refresh()
        assert _issue(hass, mock_config_entry) is None
        assert coordinator.last_update_success is True

        # The counter restarted: two more failures do not bring the issue back.
        mock_fetch.side_effect = Concept2ConnectionError("boom")
        await coordinator.async_refresh()
        await coordinator.async_refresh()

    assert _issue(hass, mock_config_entry) is None


async def test_removing_entry_deletes_repair_issue(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Removing the integration removes its repair issue."""
    mock_fetch = AsyncMock(return_value=RESULT)
    with patch(RESULT_PATH, mock_fetch):
        coordinator = await _set_up(hass, mock_config_entry, mock_fetch)
        mock_fetch.side_effect = Concept2ConnectionError("boom")
        for _ in range(3):
            await coordinator.async_refresh()
        assert _issue(hass, mock_config_entry) is not None

        await hass.config_entries.async_remove(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert _issue(hass, mock_config_entry) is None
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
