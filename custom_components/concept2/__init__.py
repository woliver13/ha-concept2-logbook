"""The Concept2 Logbook integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .api import Concept2ApiClient
from .const import NIGHTLY_REFRESH_HOUR, NIGHTLY_REFRESH_MINUTE
from .coordinator import Concept2DataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Concept2 Logbook from a config entry."""
    client = Concept2ApiClient(hass, entry.data[CONF_ACCESS_TOKEN])
    coordinator = Concept2DataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    @callback
    def _async_nightly_refresh(now: datetime) -> None:
        """Refresh at the fixed nightly time, via the same path as the refresh button."""
        hass.async_create_task(coordinator.async_request_refresh())

    # async_track_time_change matches against HA's configured local time zone.
    entry.async_on_unload(
        async_track_time_change(
            hass,
            _async_nightly_refresh,
            hour=NIGHTLY_REFRESH_HOUR,
            minute=NIGHTLY_REFRESH_MINUTE,
            second=0,
        )
    )

    # Reload when the token changes (reauth or options flow) so the client picks it up.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its data changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
