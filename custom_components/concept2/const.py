"""Constants for the Concept2 Logbook integration."""

import logging

DOMAIN = "concept2"
LOGGER = logging.getLogger(__package__)

API_BASE_URL = "https://log.concept2.com/api"
ROWER_RESULT_TYPE = "rower"

MANUFACTURER = "Concept2"

# Options-flow keys for the user-configurable nightly poll time.
CONF_REFRESH_HOUR = "refresh_hour"
CONF_REFRESH_MINUTE = "refresh_minute"

# Default local wall-clock time of the nightly poll (hour, minute), used until the user
# sets their own via the options flow — deterministic across restarts.
DEFAULT_REFRESH_HOUR = 3
DEFAULT_REFRESH_MINUTE = 0

# Consecutive failed polls before a repair issue is raised.
FAILURES_BEFORE_REPAIR_ISSUE = 3
