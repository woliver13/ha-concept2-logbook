"""Tests for the Concept2 Logbook diagnostics download."""

import json
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.concept2.api import Concept2ConnectionError
from custom_components.concept2.diagnostics import async_get_config_entry_diagnostics

REQUEST_PATH = "custom_components.concept2.api.Concept2ApiClient._request"
RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"

TOKEN = "existing-token"

PAYLOAD = {
    "data": [
        {
            "id": 111,
            "user_id": 12345,
            "type": "rower",
            "date": "2026-09-15T08:00:00",
            "distance": 6000,
            "time": 13500,
            "comments": "felt strong; door code 4242",
            "calories_total": 450,
            "stroke_count": 900,
            "stroke_rate": 24,
            "drag_factor": 128,
            "workout": {
                "splits": [
                    {
                        "time": 2400,
                        "distance": 867,
                        "heart_rate": {"average": 151, "ending": 173},
                    }
                ]
            },
        }
    ]
}


async def test_diagnostics_has_state_and_raw_response_without_the_token(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """The payload has coordinator state and the raw response, and no token or personal data."""
    mock_config_entry.add_to_hass(hass)
    with patch(REQUEST_PATH, AsyncMock(return_value=PAYLOAD)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    coordinator = diagnostics["coordinator"]
    assert coordinator["last_update_success"] is True
    assert coordinator["consecutive_failures"] == 0
    assert coordinator["data"]["distance_meters"] == 6000

    raw_result = diagnostics["last_raw_response"]["data"][0]
    assert raw_result["distance"] == 6000
    assert raw_result["type"] == "rower"

    dumped = json.dumps(diagnostics, default=str)
    assert TOKEN not in dumped
    assert "12345" not in dumped
    assert "door code" not in dumped
    assert "151" not in dumped
    assert "173" not in dumped
    assert diagnostics["last_raw_response"]["data"][0]["workout"]["splits"][0]["distance"] == 867
    assert diagnostics["entry"]["data"]["access_token"] == "**REDACTED**"


async def test_diagnostics_reports_failures(hass: HomeAssistant, mock_config_entry) -> None:
    """After a failed poll the payload shows the failure, keeps the last response, and hides the token."""
    mock_config_entry.add_to_hass(hass)
    with patch(REQUEST_PATH, AsyncMock(return_value=PAYLOAD)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    with patch(RESULT_PATH, AsyncMock(side_effect=Concept2ConnectionError("boom"))):
        await coordinator.async_refresh()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["coordinator"]["last_update_success"] is False
    assert diagnostics["coordinator"]["consecutive_failures"] == 1
    assert "boom" in diagnostics["coordinator"]["last_exception"]
    assert diagnostics["last_raw_response"]["data"][0]["distance"] == 6000
    assert TOKEN not in json.dumps(diagnostics, default=str)


async def test_diagnostics_before_any_response(hass: HomeAssistant, mock_config_entry) -> None:
    """With no response yet the raw response is None."""
    mock_config_entry.add_to_hass(hass)
    with patch(RESULT_PATH, AsyncMock(return_value=None)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert diagnostics["last_raw_response"] is None
    assert diagnostics["coordinator"]["data"] is None
