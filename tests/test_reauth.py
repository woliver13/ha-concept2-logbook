"""Tests for the Concept2 Logbook reauth and options flows."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.concept2.api import Concept2AuthError, Concept2ConnectionError
from custom_components.concept2.const import DOMAIN

RESULT_PATH = "custom_components.concept2.api.Concept2ApiClient.async_get_latest_rower_result"
USER_ID_PATH = "custom_components.concept2.config_flow.Concept2ApiClient.async_get_user_id"
NEW_TOKEN = "new-token"


def _last_workout_date_registered(hass: HomeAssistant, entry) -> bool:
    registry = er.async_get(hass)
    unique_id = f"concept2_{entry.unique_id}_last_workout_date"
    return registry.async_get_entity_id("sensor", DOMAIN, unique_id) is not None


async def _setup(hass: HomeAssistant, entry) -> None:
    entry.add_to_hass(hass)
    with patch(RESULT_PATH, AsyncMock(return_value=None)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


def _reauth_flows(hass: HomeAssistant) -> list:
    return [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"]["source"] == config_entries.SOURCE_REAUTH
    ]


async def test_401_starts_reauth_and_valid_token_resolves_it(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A 401 on refresh starts reauth; a valid new token resolves it, keeping entities."""
    await _setup(hass, mock_config_entry)
    assert _last_workout_date_registered(hass, mock_config_entry)

    with patch(RESULT_PATH, AsyncMock(side_effect=Concept2AuthError("revoked"))):
        await mock_config_entry.runtime_data.async_refresh()
        await hass.async_block_till_done()

    flows = _reauth_flows(hass)
    assert len(flows) == 1
    assert flows[0]["step_id"] == "reauth_confirm"

    with patch(USER_ID_PATH, AsyncMock(return_value="12345")), patch(
        RESULT_PATH, AsyncMock(return_value=None)
    ):
        result = await hass.config_entries.flow.async_configure(
            flows[0]["flow_id"], {CONF_ACCESS_TOKEN: NEW_TOKEN}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == NEW_TOKEN
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert not _reauth_flows(hass)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert _last_workout_date_registered(hass, mock_config_entry)


async def test_401_at_setup_starts_reauth_and_resolves(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """A token already revoked at startup also reaches reauth and recovers on reload."""
    mock_config_entry.add_to_hass(hass)
    with patch(RESULT_PATH, AsyncMock(side_effect=Concept2AuthError("revoked"))):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    flows = _reauth_flows(hass)
    assert len(flows) == 1

    with patch(USER_ID_PATH, AsyncMock(return_value="12345")), patch(
        RESULT_PATH, AsyncMock(return_value=None)
    ):
        await hass.config_entries.flow.async_configure(
            flows[0]["flow_id"], {CONF_ACCESS_TOKEN: NEW_TOKEN}
        )
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == NEW_TOKEN


async def test_reauth_rejects_bad_tokens(hass: HomeAssistant, mock_config_entry) -> None:
    """Invalid or wrong-account tokens keep the form open and leave the token alone."""
    await _setup(hass, mock_config_entry)
    mock_config_entry.async_start_reauth(hass)
    await hass.async_block_till_done()
    flow_id = _reauth_flows(hass)[0]["flow_id"]

    with patch(USER_ID_PATH, AsyncMock(side_effect=Concept2AuthError("bad"))):
        result = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_ACCESS_TOKEN: "bad"}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(USER_ID_PATH, AsyncMock(return_value="99999")):
        result = await hass.config_entries.flow.async_configure(
            flow_id, {CONF_ACCESS_TOKEN: "other-account"}
        )
    assert result["errors"] == {"base": "wrong_account"}
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == "existing-token"


async def test_options_flow_rotates_token(hass: HomeAssistant, mock_config_entry) -> None:
    """The options flow validates a new token and updates the entry in place."""
    await _setup(hass, mock_config_entry)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    with patch(USER_ID_PATH, AsyncMock(return_value="12345")), patch(
        RESULT_PATH, AsyncMock(return_value=None)
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: NEW_TOKEN}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == NEW_TOKEN
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert _last_workout_date_registered(hass, mock_config_entry)


async def test_options_flow_validation_errors(hass: HomeAssistant, mock_config_entry) -> None:
    """The options flow reports the same errors as initial setup and keeps the old token."""
    await _setup(hass, mock_config_entry)
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    for side_effect, expected in (
        (Concept2AuthError("bad"), "invalid_auth"),
        (Concept2ConnectionError("down"), "cannot_connect"),
    ):
        with patch(USER_ID_PATH, AsyncMock(side_effect=side_effect)):
            result = await hass.config_entries.options.async_configure(
                result["flow_id"], {CONF_ACCESS_TOKEN: NEW_TOKEN}
            )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": expected}

    with patch(USER_ID_PATH, AsyncMock(return_value="99999")):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_ACCESS_TOKEN: NEW_TOKEN}
        )
    assert result["errors"] == {"base": "wrong_account"}
    assert mock_config_entry.data[CONF_ACCESS_TOKEN] == "existing-token"
