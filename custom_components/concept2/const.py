"""Constants for the Concept2 Logbook integration."""

import logging

DOMAIN = "concept2"
LOGGER = logging.getLogger(__package__)

API_BASE_URL = "https://log.concept2.com/api"
ROWER_RESULT_TYPE = "rower"

MANUFACTURER = "Concept2"

# Fixed local wall-clock time of the nightly poll (hour, minute) — deterministic across restarts.
NIGHTLY_REFRESH_HOUR = 3
NIGHTLY_REFRESH_MINUTE = 0
