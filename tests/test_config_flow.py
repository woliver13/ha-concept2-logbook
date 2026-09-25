"""Tests for the Concept2 Logbook config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.concept2.api import Concept2AuthError, Concept2ConnectionError
from custom_components.concept2.const import DOMAIN

VALID_TOKEN = "valid-token"
API_CLIENT_PATH = "custom_components.concept2.config_flow.Concept2ApiClient.async_get_user_id"


async def _start_flow(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """A valid token creates a config entry keyed by the Concept2 user id."""
    result = await _start_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(API_CLIENT_PATH, AsyncMock(return_value="12345")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: VALID_TOKEN}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ACCESS_TOKEN: VALID_TOKEN}

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].unique_id == "12345"


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """An invalid token surfaces invalid_auth and does not create an entry."""
    result = await _start_flow(hass)

    with patch(API_CLIENT_PATH, AsyncMock(side_effect=Concept2AuthError("bad token"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: "bad-token"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """An unreachable API surfaces cannot_connect and does not create an entry."""
    result = await _start_flow(hass)

    with patch(API_CLIENT_PATH, AsyncMock(side_effect=Concept2ConnectionError("timeout"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: VALID_TOKEN}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert not hass.config_entries.async_entries(DOMAIN)


async def test_user_flow_duplicate_account(hass: HomeAssistant, mock_config_entry) -> None:
    """A second setup attempt for the same Concept2 user id is rejected as a duplicate."""
    mock_config_entry.add_to_hass(hass)

    result = await _start_flow(hass)
    with patch(API_CLIENT_PATH, AsyncMock(return_value=mock_config_entry.unique_id)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: VALID_TOKEN}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
