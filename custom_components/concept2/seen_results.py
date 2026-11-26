"""Tracks which Concept2 results have already been seen, to detect new ones."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import Concept2Result
from .const import (
    DOMAIN,
    FLOOD_GUARD_MAX_EVENTS_PER_POLL,
    LOGGER,
    MAX_SEEN_RESULT_IDS,
    SEEN_RESULTS_STORAGE_VERSION,
)


class Concept2SeenResultsTracker:
    """Persists which result ids have been seen, bounding the stored set.

    On first use — no stored state yet, or a store that fails to load — every
    currently fetched result is treated as the baseline: recorded as seen, none
    reported as new. This guarantees pre-existing history never floods automations,
    and that a lost/corrupted store falls back to the same safe behavior rather than
    re-firing history.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Set up the per-entry store."""
        self._store: Store[dict[str, list[int]]] = Store(
            hass, SEEN_RESULTS_STORAGE_VERSION, f"{DOMAIN}_seen_results_{entry.entry_id}"
        )

    async def async_detect_new_results(
        self, results: list[Concept2Result]
    ) -> list[Concept2Result]:
        """Return the subset of `results` (ascending by date) not yet seen.

        Capped by the flood guard — results beyond the cap are marked seen but not
        returned. Marks every id in `results` as seen. Only call this after a
        successful poll; a failed poll must never reach here, so nothing is lost.
        """
        stored_ids = await self._async_load_seen_ids()
        is_first_run = stored_ids is None
        seen_ids = set(stored_ids) if stored_ids is not None else set()

        new_results = [] if is_first_run else [
            result for result in results if result.result_id not in seen_ids
        ]

        if len(new_results) > FLOOD_GUARD_MAX_EVENTS_PER_POLL:
            LOGGER.warning(
                "Concept2: %d new results in one poll exceeds the flood guard (%d); "
                "firing the oldest %d and marking the rest seen without firing them",
                len(new_results),
                FLOOD_GUARD_MAX_EVENTS_PER_POLL,
                FLOOD_GUARD_MAX_EVENTS_PER_POLL,
            )
            to_fire = new_results[:FLOOD_GUARD_MAX_EVENTS_PER_POLL]
        else:
            to_fire = new_results

        updated_order = [] if is_first_run else list(stored_ids)
        for result in results:
            if result.result_id not in seen_ids:
                updated_order.append(result.result_id)
                seen_ids.add(result.result_id)
        updated_order = updated_order[-MAX_SEEN_RESULT_IDS:]

        await self._store.async_save({"seen_result_ids": updated_order})
        return to_fire

    async def _async_load_seen_ids(self) -> list[int] | None:
        """Return the stored seen-id list, or None if there's no usable stored state.

        None covers both "nothing stored yet" and "the stored state is corrupted" —
        both get identical baseline treatment by the caller.
        """
        try:
            data = await self._store.async_load()
        except Exception:  # noqa: BLE001 - any load failure means "no usable state"
            LOGGER.warning(
                "Concept2: stored seen-results state is corrupted; falling back to baseline"
            )
            return None
        if data is None:
            return None
        return data.get("seen_result_ids", [])
