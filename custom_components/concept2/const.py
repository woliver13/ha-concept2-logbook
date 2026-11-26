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

# Options-flow key for the optional sub-daily polling interval. Unset (None) means off,
# so every upgraded install keeps today's nightly-only behavior until a user opts in.
CONF_POLL_INTERVAL_MINUTES = "poll_interval_minutes"

# Minimum allowed value for the above, chosen to stay well clear of Concept2's API rate
# limits for a personal-access-token client polling on its own schedule.
MIN_POLL_INTERVAL_MINUTES = 15

# Consecutive failed polls before a repair issue is raised.
FAILURES_BEFORE_REPAIR_ISSUE = 3

# The new-workout event entity's single event type.
EVENT_TYPE_WORKOUT_LOGGED = "workout_logged"

# How many seen result ids to keep per config entry, oldest dropped first.
MAX_SEEN_RESULT_IDS = 50

# Flood guard: at most this many workout_logged events fire from one poll.
FLOOD_GUARD_MAX_EVENTS_PER_POLL = 10

# Storage schema version for the per-entry seen-results store.
SEEN_RESULTS_STORAGE_VERSION = 1
