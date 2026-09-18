"""Shared fixtures for Concept2 Logbook tests."""

import socket as _socket_module
import sys

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_ACCESS_TOKEN

from custom_components.concept2.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"

if sys.platform == "win32":
    # Every asyncio event loop needs a self-pipe, and on Windows that's always a
    # loopback AF_INET socket.socketpair() (there's no real AF_UNIX socketpair
    # here) — so creating *any* event loop trips HA's test-harness socket-blocking
    # fixture (pytest-socket) before a single test even runs, since it only
    # exempts AF_UNIX. This wraps socket.socketpair so it always uses the real,
    # unguarded socket class for that one internal call, while leaving actual
    # test/application code's socket.socket() calls blocked as intended.
    _real_socket_class = _socket_module.socket
    _real_socketpair = _socket_module.socketpair

    def _unguarded_socketpair(*args, **kwargs):
        previous = _socket_module.socket
        _socket_module.socket = _real_socket_class
        try:
            return _real_socketpair(*args, **kwargs)
        finally:
            _socket_module.socket = previous

    _socket_module.socketpair = _unguarded_socketpair


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components/ visible to every test in this suite."""
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a Concept2 Logbook config entry for an already-configured account."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="12345",
        data={CONF_ACCESS_TOKEN: "existing-token"},
        title="Concept2 Logbook",
    )
