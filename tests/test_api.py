"""Tests for the Concept2 Logbook API client."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant

from custom_components.concept2.api import Concept2ApiClient

REQUEST_PATH = "custom_components.concept2.api.Concept2ApiClient._request"


def _raw_result(result_id: int, result_type: str, date: str) -> dict:
    return {
        "id": result_id,
        "type": result_type,
        "date": date,
        "distance": 6000,
        "time": 13500,
        "calories_total": 450,
        "stroke_count": 900,
        "stroke_rate": 24,
        "drag_factor": 128,
    }


async def test_bike_and_ski_results_are_filtered_out(hass: HomeAssistant) -> None:
    """Only `rower` results are considered when picking the latest result."""
    payload = {
        "data": [
            _raw_result(1, "rower", "2026-09-10T08:00:00"),
            _raw_result(2, "bike", "2026-09-20T08:00:00"),
            _raw_result(3, "ski", "2026-09-21T08:00:00"),
        ]
    }
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        result = await client.async_get_latest_rower_result()

    assert result is not None
    assert result.result_id == 1


async def test_most_recent_rower_result_is_selected(hass: HomeAssistant) -> None:
    """Among multiple rower results, the most recent by date wins, ignoring newer non-rower ones."""
    payload = {
        "data": [
            _raw_result(1, "rower", "2026-09-10T08:00:00"),
            _raw_result(2, "rower", "2026-09-20T08:00:00"),
            _raw_result(3, "bike", "2026-09-25T08:00:00"),
        ]
    }
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        result = await client.async_get_latest_rower_result()

    assert result is not None
    assert result.result_id == 2


async def test_no_rower_results_returns_none(hass: HomeAssistant) -> None:
    """Returns None when the API has results but none are type `rower`."""
    payload = {"data": [_raw_result(1, "bike", "2026-09-20T08:00:00")]}
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        result = await client.async_get_latest_rower_result()

    assert result is None
