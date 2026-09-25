"""Config flow for the Concept2 Logbook integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .api import Concept2ApiClient, Concept2ApiError, Concept2AuthError, Concept2ConnectionError
from .const import DOMAIN, LOGGER

STEP_TOKEN_DATA_SCHEMA = vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})


async def _async_validate_token(
    hass: HomeAssistant, token: str
) -> tuple[str | None, str | None]:
    """Validate a token against the Concept2 API.

    Returns (user_id, None) on success or (None, error_key) on failure. Shared by the
    initial setup, reauth and options flows so they all validate identically.
    """
    client = Concept2ApiClient(hass, token)
    try:
        return await client.async_get_user_id(), None
    except Concept2AuthError:
        return None, "invalid_auth"
    except Concept2ConnectionError:
        return None, "cannot_connect"
    except Concept2ApiError:
        LOGGER.exception("Unexpected error validating Concept2 access token")
        return None, "unknown"


class Concept2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Concept2 Logbook."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> Concept2OptionsFlow:
        """Return the options flow, used to rotate the access token."""
        return Concept2OptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step: collect and validate an access token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_id, error = await _async_validate_token(
                self.hass, user_input[CONF_ACCESS_TOKEN]
            )
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Concept2 Logbook", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_TOKEN_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Start reauth after the coordinator got a 401."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect a new token, keeping the existing entry, device and entities."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _async_validate_entry_token(
                self.hass, entry, user_input[CONF_ACCESS_TOKEN]
            )
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN]}
                )
                # A loaded entry is reloaded by its update listener; one whose setup failed
                # on the 401 has no listener registered, so reload it here.
                if entry.state is not ConfigEntryState.LOADED:
                    await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_TOKEN_DATA_SCHEMA, errors=errors
        )


async def _async_validate_entry_token(
    hass: HomeAssistant, entry: ConfigEntry, token: str
) -> str | None:
    """Validate a replacement token; it must belong to the entry's Concept2 account."""
    user_id, error = await _async_validate_token(hass, token)
    if error:
        return error
    if user_id != entry.unique_id:
        return "wrong_account"
    return None


class Concept2OptionsFlow(OptionsFlow):
    """Let the user proactively rotate their access token."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Remember the entry being configured."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store a new access token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            error = await _async_validate_entry_token(
                self.hass, self._entry, user_input[CONF_ACCESS_TOKEN]
            )
            if error:
                errors["base"] = error
            else:
                # The entry's update listener reloads it with the new token.
                self.hass.config_entries.async_update_entry(
                    self._entry,
                    data={**self._entry.data, CONF_ACCESS_TOKEN: user_input[CONF_ACCESS_TOKEN]},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init", data_schema=STEP_TOKEN_DATA_SCHEMA, errors=errors
        )
