"""Config flow for the Concept2 Logbook integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResult

from .api import Concept2ApiClient, Concept2ApiError, Concept2AuthError, Concept2ConnectionError
from .const import DOMAIN, LOGGER

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str})


class Concept2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Concept2 Logbook."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step: collect and validate an access token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = Concept2ApiClient(self.hass, user_input[CONF_ACCESS_TOKEN])
            try:
                user_id = await client.async_get_user_id()
            except Concept2AuthError:
                errors["base"] = "invalid_auth"
            except Concept2ConnectionError:
                errors["base"] = "cannot_connect"
            except Concept2ApiError:
                LOGGER.exception("Unexpected error validating Concept2 access token")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Concept2 Logbook", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
