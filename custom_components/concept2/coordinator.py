"""Data update coordinator for the Concept2 Logbook integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    Concept2ApiClient,
    Concept2AuthError,
    Concept2ConnectionError,
    Concept2Result,
)
from .const import DOMAIN, FAILURES_BEFORE_REPAIR_ISSUE, LOGGER


class Concept2DataUpdateCoordinator(DataUpdateCoordinator[Concept2Result | None]):
    """Fetches the latest logged rower result from the Concept2 API.

    There is no rolling update_interval: refreshes happen on setup, at a fixed local
    nightly time (registered in __init__.py), and on demand via the refresh button.

    Failures other than a bad token raise UpdateFailed, so the last good result is kept.
    After FAILURES_BEFORE_REPAIR_ISSUE failures in a row a repair issue is raised, and the
    next successful poll clears it.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: Concept2ApiClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=None)
        self.config_entry = entry
        self._client = client
        self._consecutive_failures = 0

    @property
    def consecutive_failures(self) -> int:
        """Return how many polls in a row have failed."""
        return self._consecutive_failures

    @property
    def last_raw_response(self) -> dict | None:
        """Return the last raw results response from the API, if there was one."""
        return self._client.last_response

    @property
    def issue_id(self) -> str:
        """Return the id of this entry's poll-failure repair issue."""
        return f"poll_failing_{self.config_entry.entry_id}"

    async def _async_update_data(self) -> Concept2Result | None:
        """Fetch the latest rower result from the Concept2 API."""
        try:
            result = await self._client.async_get_latest_rower_result()
        except Concept2AuthError as err:
            raise ConfigEntryAuthFailed("Concept2 access token is no longer valid") from err
        except Concept2ConnectionError as err:
            self._async_record_failure(err)
            raise UpdateFailed(str(err)) from err

        self._consecutive_failures = 0
        ir.async_delete_issue(self.hass, DOMAIN, self.issue_id)
        return result

    def _async_record_failure(self, err: Exception) -> None:
        """Count a failed poll and raise the repair issue once there are enough in a row."""
        self._consecutive_failures += 1
        LOGGER.warning(
            "Concept2 poll failed (%s in a row): %s; will retry at the next refresh",
            self._consecutive_failures,
            err,
        )
        if self._consecutive_failures >= FAILURES_BEFORE_REPAIR_ISSUE:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                self.issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="poll_failing",
                translation_placeholders={"failures": str(self._consecutive_failures)},
            )
