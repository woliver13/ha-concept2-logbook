"""Tests for new-result detection, the persisted baseline, and the workout_logged event."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.concept2.api import Concept2ConnectionError, Concept2Result
from custom_components.concept2.const import DOMAIN, EVENT_TYPE_WORKOUT_LOGGED

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_recent_rower_results"
REQUEST_PATH = "custom_components.concept2.api.Concept2ApiClient._request"


def _result(result_id: int, date: datetime, distance_meters: float = 6000) -> Concept2Result:
    return Concept2Result(
        result_id=result_id,
        date=dt_util.as_utc(date),
        distance_meters=distance_meters,
        duration_seconds=1350.0,
        calories_total=450,
        stroke_count=900,
        stroke_rate=24,
        drag_factor=128,
    )


def _raw_result(result_id: int, result_type: str, date: str) -> dict:
    return {
        "id": result_id,
        "type": result_type,
        "date": date,
        "distance": 6000,
        "time": 13500,
    }


def _event_entity_id(hass: HomeAssistant, mock_config_entry) -> str:
    registry = er.async_get(hass)
    unique_id = f"concept2_{mock_config_entry.unique_id}_new_workout"
    entity_id = registry.async_get_entity_id("event", DOMAIN, unique_id)
    assert entity_id is not None
    return entity_id


def _fired_for(events: list[Event], entity_id: str) -> list[Event]:
    """Return the captured state_changed events that are this entity firing a new event.

    Excludes the state_changed event every entity gets just from being added to hass
    (old_state=None, no event_type attribute yet) — only a real `_trigger_event` call
    sets `event_type`.
    """
    return [
        event
        for event in events
        if event.data.get("entity_id") == entity_id
        and event.data["new_state"] is not None
        and event.data["new_state"].attributes.get("event_type") == EVENT_TYPE_WORKOUT_LOGGED
    ]


async def _setup(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch, mock_fetch: AsyncMock
) -> None:
    """Set up the entry with `mock_fetch` patched in for the whole test, not just setup.

    Uses monkeypatch (test-scoped) rather than `with patch(...)`, since several tests
    mutate `mock_fetch` and trigger further refreshes — including through a config entry
    reload — well after this function returns.
    """
    monkeypatch.setattr(RESULT_PATH, mock_fetch)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()


async def test_first_setup_records_baseline_and_fires_nothing(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-existing history on first setup is recorded as seen but never fired."""
    events = async_capture_events(hass, "state_changed")
    existing = [
        _result(1, datetime(2026, 9, 10, 8, 0, 0)),
        _result(2, datetime(2026, 9, 15, 8, 0, 0)),
    ]
    await _setup(hass, mock_config_entry, monkeypatch, AsyncMock(return_value=existing))

    entity_id = _event_entity_id(hass, mock_config_entry)
    assert _fired_for(events, entity_id) == []
    assert hass.states.get(entity_id).state == STATE_UNKNOWN


async def test_one_new_result_fires_one_event_with_full_payload(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A result that's new since the baseline fires exactly one event with the full payload."""
    events = async_capture_events(hass, "state_changed")
    existing = [_result(1, datetime(2026, 9, 10, 8, 0, 0))]
    mock_fetch = AsyncMock(return_value=existing)
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)
    entity_id = _event_entity_id(hass, mock_config_entry)

    new_result = _result(2, datetime(2026, 9, 20, 8, 0, 0), distance_meters=6000)
    mock_fetch.return_value = [*existing, new_result]
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    fired = _fired_for(events, entity_id)
    assert len(fired) == 1
    attrs = fired[0].data["new_state"].attributes
    assert attrs["event_type"] == EVENT_TYPE_WORKOUT_LOGGED
    assert attrs["result_id"] == 2
    assert attrs["date"] == new_result.date.isoformat()
    assert attrs["distance_meters"] == 6000
    assert attrs["duration_seconds"] == 1350.0
    assert attrs["pace_500m_seconds"] == pytest.approx(1350.0 / (6000 / 500))
    assert attrs["calories_total"] == 450
    assert attrs["stroke_count"] == 900
    assert attrs["stroke_rate"] == 24
    assert attrs["drag_factor"] == 128
    assert attrs["heart_rate_avg"] is None
    assert attrs["heart_rate_ending"] is None


async def test_two_new_results_fire_oldest_first(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two results logged between polls fire two events, oldest first."""
    events = async_capture_events(hass, "state_changed")
    mock_fetch = AsyncMock(return_value=[])
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)
    entity_id = _event_entity_id(hass, mock_config_entry)

    older = _result(1, datetime(2026, 9, 10, 8, 0, 0))
    newer = _result(2, datetime(2026, 9, 20, 8, 0, 0))
    mock_fetch.return_value = [older, newer]
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    fired = _fired_for(events, entity_id)
    assert [event.data["new_state"].attributes["result_id"] for event in fired] == [1, 2]


async def test_restart_with_persisted_state_does_not_refire(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reloading the entry (simulating an HA restart) does not re-fire already-seen results."""
    existing = [_result(1, datetime(2026, 9, 10, 8, 0, 0))]
    mock_fetch = AsyncMock(return_value=existing)
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)

    events = async_capture_events(hass, "state_changed")
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _event_entity_id(hass, mock_config_entry)
    assert _fired_for(events, entity_id) == []


async def test_result_new_at_startup_fires_once_entity_is_added(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A result that's new on the refresh that runs before platforms are set up still fires.

    `async_config_entry_first_refresh` completes before the event entity exists, so this
    guards against silently dropping a result logged while HA was down.
    """
    existing = [_result(1, datetime(2026, 9, 10, 8, 0, 0))]
    mock_fetch = AsyncMock(return_value=existing)
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)

    events = async_capture_events(hass, "state_changed")
    new_result = _result(2, datetime(2026, 9, 20, 8, 0, 0))
    mock_fetch.return_value = [*existing, new_result]
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _event_entity_id(hass, mock_config_entry)
    fired = _fired_for(events, entity_id)
    assert len(fired) == 1
    assert fired[0].data["new_state"].attributes["result_id"] == 2


async def test_back_dated_entry_fires_once(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A back-dated manual entry (new id, older date) fires once and never again."""
    events = async_capture_events(hass, "state_changed")
    existing = _result(5, datetime(2026, 9, 20, 8, 0, 0))
    mock_fetch = AsyncMock(return_value=[existing])
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)
    entity_id = _event_entity_id(hass, mock_config_entry)

    back_dated = _result(99, datetime(2026, 9, 5, 8, 0, 0))
    mock_fetch.return_value = [back_dated, existing]
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    fired = _fired_for(events, entity_id)
    assert len(fired) == 1
    assert fired[0].data["new_state"].attributes["result_id"] == 99

    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert len(_fired_for(events, entity_id)) == 1


async def test_bike_and_ski_results_never_fire(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bike and ski-erg results never fire, even mixed in with the fetched page."""
    events = async_capture_events(hass, "state_changed")
    mock_request = AsyncMock(return_value={"data": []})
    monkeypatch.setattr(REQUEST_PATH, mock_request)
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity_id = _event_entity_id(hass, mock_config_entry)

    mock_request.return_value = {
        "data": [
            _raw_result(1, "bike", "2026-09-20T08:00:00"),
            _raw_result(2, "ski", "2026-09-21T08:00:00"),
        ]
    }
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    assert _fired_for(events, entity_id) == []


async def test_failed_poll_marks_nothing_seen_next_success_fires_missed(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed poll loses nothing; the next successful poll fires the missed result."""
    events = async_capture_events(hass, "state_changed")
    mock_fetch = AsyncMock(return_value=[])
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)
    entity_id = _event_entity_id(hass, mock_config_entry)

    missed_result = _result(1, datetime(2026, 9, 20, 8, 0, 0))
    mock_fetch.side_effect = Concept2ConnectionError("boom")
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert _fired_for(events, entity_id) == []

    mock_fetch.side_effect = None
    mock_fetch.return_value = [missed_result]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    fired = _fired_for(events, entity_id)
    assert len(fired) == 1
    assert fired[0].data["new_state"].attributes["result_id"] == 1


async def test_corrupted_store_falls_back_to_baseline(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A store that fails to load falls back to baseline instead of re-firing history."""
    events = async_capture_events(hass, "state_changed")
    existing = [_result(1, datetime(2026, 9, 10, 8, 0, 0))]
    mock_fetch = AsyncMock(return_value=existing)

    with patch(
        "custom_components.concept2.seen_results.Store.async_load",
        AsyncMock(side_effect=OSError("disk read error")),
    ):
        await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)

    entity_id = _event_entity_id(hass, mock_config_entry)
    assert _fired_for(events, entity_id) == []

    # The fallback baseline was actually persisted: a normal next poll doesn't re-fire it.
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert _fired_for(events, entity_id) == []


async def test_flood_guard_caps_events_and_marks_rest_seen(
    hass: HomeAssistant, mock_config_entry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """More new results than the flood-guard cap in one poll fire only up to the cap."""
    events = async_capture_events(hass, "state_changed")
    mock_fetch = AsyncMock(return_value=[])
    await _setup(hass, mock_config_entry, monkeypatch, mock_fetch)
    entity_id = _event_entity_id(hass, mock_config_entry)

    flood = [
        _result(i, datetime(2026, 9, 1, 8, 0, 0) + timedelta(days=i)) for i in range(1, 15)
    ]
    mock_fetch.return_value = flood
    coordinator = mock_config_entry.runtime_data
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    fired = _fired_for(events, entity_id)
    assert [event.data["new_state"].attributes["result_id"] for event in fired] == list(
        range(1, 11)
    )

    # The overflowed results were still marked seen — a later poll fires no additional events.
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert len(_fired_for(events, entity_id)) == 10
