"""Data update coordinator for the Concept2 Logbook integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    Concept2ApiClient,
    Concept2AuthError,
    Concept2ConnectionError,
    Concept2Result,
)
from .const import DOMAIN, LOGGER


class Concept2DataUpdateCoordinator(DataUpdateCoordinator[Concept2Result | None]):
    """Fetches the latest logged rower result from the Concept2 API.

    There is no rolling update_interval: refreshes happen on setup, at a fixed local
    nightly time (registered in __init__.py), and on demand via the refresh button.
    """

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: Concept2ApiClient
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=None)
        self.config_entry = entry
        self._client = client

    async def _async_update_data(self) -> Concept2Result | None:
        """Fetch the latest rower result from the Concept2 API."""
        try:
            return await self._client.async_get_latest_rower_result()
        except Concept2AuthError as err:
            raise ConfigEntryAuthFailed("Concept2 access token is no longer valid") from err
        except Concept2ConnectionError as err:
            raise UpdateFailed(str(err)) from err
