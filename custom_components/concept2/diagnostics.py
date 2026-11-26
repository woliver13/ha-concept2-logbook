"""Diagnostics support for the Concept2 Logbook integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

# The token, anything that identifies the rower, free text they typed, and heart rate
# readings (both the raw per-split API shape and the parsed result's summary fields).
TO_REDACT = {
    CONF_ACCESS_TOKEN,
    "unique_id",
    "user_id",
    "comments",
    "heart_rate",
    "heart_rate_avg",
    "heart_rate_ending",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with the token and personal data redacted."""
    coordinator = entry.runtime_data
    data = asdict(coordinator.data)
    if data["latest"] is not None:
        data["latest"]["date"] = data["latest"]["date"].isoformat()
    for new_result in data["new_results"]:
        new_result["date"] = new_result["date"].isoformat()

    return async_redact_data(
        {
            "entry": entry.as_dict(),
            "coordinator": {
                "last_update_success": coordinator.last_update_success,
                "last_exception": repr(coordinator.last_exception)
                if coordinator.last_exception
                else None,
                "consecutive_failures": coordinator.consecutive_failures,
                "data": data,
            },
            "last_raw_response": coordinator.last_raw_response,
        },
        TO_REDACT,
    )
