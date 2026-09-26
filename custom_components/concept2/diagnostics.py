"""Diagnostics support for the Concept2 Logbook integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

# The token, and anything that identifies the rower or holds free text they typed.
TO_REDACT = {CONF_ACCESS_TOKEN, "unique_id", "user_id", "comments"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with the token and personal data redacted."""
    coordinator = entry.runtime_data
    data = asdict(coordinator.data) if coordinator.data is not None else None
    if data is not None:
        data["date"] = data["date"].isoformat()

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
