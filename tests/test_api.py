"""Tests for the Concept2 Logbook API client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.concept2.api import Concept2ApiClient, Concept2ConnectionError

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
    """Only `rower` results are returned."""
    payload = {
        "data": [
            _raw_result(1, "rower", "2026-09-10T08:00:00"),
            _raw_result(2, "bike", "2026-09-20T08:00:00"),
            _raw_result(3, "ski", "2026-09-21T08:00:00"),
        ]
    }
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        results = await client.async_get_recent_rower_results()

    assert [result.result_id for result in results] == [1]


async def test_multiple_rower_results_are_all_returned(hass: HomeAssistant) -> None:
    """All rower results come back, ignoring interleaved non-rower ones."""
    payload = {
        "data": [
            _raw_result(1, "rower", "2026-09-10T08:00:00"),
            _raw_result(2, "rower", "2026-09-20T08:00:00"),
            _raw_result(3, "bike", "2026-09-25T08:00:00"),
        ]
    }
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        results = await client.async_get_recent_rower_results()

    assert [result.result_id for result in results] == [1, 2]


async def test_results_are_sorted_ascending_by_date(hass: HomeAssistant) -> None:
    """Results come back oldest-first, regardless of the API's own response order."""
    payload = {
        "data": [
            _raw_result(2, "rower", "2026-09-20T08:00:00"),
            _raw_result(1, "rower", "2026-09-10T08:00:00"),
            _raw_result(3, "rower", "2026-09-25T08:00:00"),
        ]
    }
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        results = await client.async_get_recent_rower_results()

    assert [result.result_id for result in results] == [1, 2, 3]


async def test_no_rower_results_returns_empty_list(hass: HomeAssistant) -> None:
    """Returns an empty list when the API has results but none are type `rower`."""
    payload = {"data": [_raw_result(1, "bike", "2026-09-20T08:00:00")]}
    client = Concept2ApiClient(hass, "token")
    with patch(REQUEST_PATH, AsyncMock(return_value=payload)):
        results = await client.async_get_recent_rower_results()

    assert results == []


async def test_timeout_is_reported_as_a_connection_error(hass: HomeAssistant) -> None:
    """A request timeout (not an aiohttp.ClientError) is still a connection error."""
    client = Concept2ApiClient(hass, "token")
    client._session = MagicMock()
    client._session.get.side_effect = TimeoutError()

    with pytest.raises(Concept2ConnectionError):
        await client.async_get_recent_rower_results()


async def test_server_error_is_reported_as_a_connection_error(hass: HomeAssistant) -> None:
    """A 5xx response is a connection error, not an auth error."""
    response = MagicMock(status=503)
    client = Concept2ApiClient(hass, "token")
    client._session = MagicMock()
    client._session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    client._session.get.return_value.__aexit__ = AsyncMock(return_value=False)

    with pytest.raises(Concept2ConnectionError):
        await client.async_get_recent_rower_results()
