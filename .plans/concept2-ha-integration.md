# Plan: Concept2 Logbook Home Assistant Integration

> Source PRD: [docs/PRD-concept2-ha-integration.md](../docs/PRD-concept2-ha-integration.md)

## Architectural decisions

Durable decisions that apply across all phases:

- **Package layout**: `custom_components/concept2/` containing `manifest.json`,
  `config_flow.py`, `__init__.py`, `sensor.py`, `button.py`, `diagnostics.py`,
  `strings.json`, `translations/en.json`. Root-level `hacs.json` for HACS custom-repository
  installability.
- **API boundary**: `GET https://log.concept2.com/api/users/me/results`, header
  `Authorization: Bearer <token>`. Only page 1 is ever fetched; results are filtered to
  `type == "rower"` client-side; only the single most recent `rower` result is kept.
- **Entity/device identity**: the Concept2 user id (from the API) is the config entry
  `unique_id`, the HA device identifier, and the namespace prefix for every entity
  `unique_id` (e.g. `concept2_<user_id>_days_since_workout`). This is fixed from Phase 1
  onward so later phases (reauth, options flow, diagnostics) never need an identity migration.
- **`iot_class`**: `cloud_polling`.
- **Sensor shape** (fixed from Phase 2 onward):

  | Sensor | `device_class` | `state_class` | Unit |
  |---|---|---|---|
  | Last workout date | `timestamp` | — | — |
  | Last workout distance | `distance` | `measurement` | meters |
  | Last workout duration | `duration` | `measurement` | seconds |
  | Days since last workout | — | `measurement` | days |

- **Polling model**: a fixed local-time nightly trigger (not a rolling `update_interval`),
  plus an on-demand `button` entity. Both call the same coordinator refresh path.
- **Failure policy**: non-auth failures raise `UpdateFailed`, retain last-known sensor
  values, and log a warning; after 3 consecutive failures a HA repair issue is raised,
  cleared on the next success. A 401 instead triggers HA's reauth flow, not the repair-issue
  path.
- **Test stack**: `pytest-homeassistant-custom-component`, with the Concept2 API mocked
  (e.g. via `aioresponses`) and time-dependent logic (timezone day-diff, nightly trigger,
  failure-threshold counting) exercised with time-freezing rather than real clock waits.
  Anything requiring the real HAOS instance, a real Concept2 account/token, or real wall-clock
  elapsed time is out of reach for automated tests and is called out per phase as `hitl`.

---

## Phase 1: Install & Configure — Minimal Working Sensor

**Goals covered**: PRD Goals 1–2; §6.1 (files), §6.2 (data source), §6.7 (setup validation).

### What to build

The end-to-end path from "add integration in the UI" to "one real sensor value on screen."
`config_flow.py` accepts a token, makes a live test call to validate it, and distinguishes an
invalid/expired token (`invalid_auth`) from an unreachable API (`cannot_connect`). On success it
creates a config entry keyed by the Concept2 user id (rejecting a duplicate for the same
account). `__init__.py` wires up a coordinator that does a single fetch on setup (no schedule
yet), applies the `rower`-only filter, and keeps the single most recent result. `sensor.py`
exposes only `last_workout_date` for this phase, reporting `unknown` when no `rower` result
exists yet. This is intentionally the thinnest slice that is still installable and configurable
end-to-end — later phases add breadth (more sensors, scheduling, resilience), not new plumbing.

### Test approach

Automated: `pytest-homeassistant-custom-component` tests against a mocked API covering
valid-token setup, invalid-token rejection, unreachable-API rejection, duplicate-account
rejection, and the sensor's `unknown` vs. populated states. Manual: one real install on the
actual HAOS instance with a real token, since that's the only way to confirm the real UI flow
and real API round-trip actually work together.

### Acceptance criteria

- [x] `afk` Config flow rejects an invalid/expired token with `invalid_auth` and rejects an
      unreachable API with `cannot_connect` (mocked API, automated test).
- [x] `afk` Config flow succeeds with a valid mocked token and creates a config entry keyed by
      the Concept2 user id; a second attempt for the same user id is rejected as a duplicate
      (automated test).
- [x] `afk` `last_workout_date` reports `unknown` when the mocked API returns zero `rower`
      results, and reports the correct timestamp when one exists (automated test).
- [x] `hitl` Install the integration on the real HA instance, enter a real Concept2 personal
      access token, and confirm the config flow succeeds and the device/sensor appear in
      Settings → Devices & Services.

---

## Phase 2: Full Sensor Set + Rich Attributes

**Goals covered**: PRD Goal 1; §6.2 (rower filtering), §6.3 (sensors), §6.5 (edge cases).

### What to build

Extend `sensor.py` to the full set from the architectural decisions table:
`last_workout_distance`, `last_workout_duration`, and `days_since_last_workout`, each with the
correct `device_class`/`state_class`/unit. `days_since_last_workout` converts the workout
timestamp to HA's configured local timezone before computing the calendar-day difference,
reporting `0` for a same-day workout. The coordinator's `rower`-only filter (added in Phase 1)
is now verified against a mixed API response that includes `bike`/`ski` results, to confirm they
never affect any sensor. `calories_total`, `stroke_count`, `stroke_rate`, and `drag_factor` are
attached as `extra_state_attributes` on `last_workout_date`. After this phase, the integration's
full sensor surface is feature-complete except for scheduling and resilience.

### Test approach

Automated: parametrized tests asserting each sensor's value/unit/device_class against a mocked
API response, plus dedicated timezone-edge-case tests (late-night workout, midnight boundary,
same-day) using time-freezing across at least two timezones. A mixed rower/bike/ski mocked
response confirms filtering. Manual: visual spot-check on the real HA instance with a real
logged row, since automated tests can't confirm the values "look right" in the actual dashboard.

### Acceptance criteria

- [x] `afk` `last_workout_distance` and `last_workout_duration` report correct values, units,
      and `device_class`/`state_class` against a mocked `rower` result (automated test).
- [x] `afk` `days_since_last_workout` is correct across a local-timezone midnight boundary and
      reports `0` for a same-day workout (automated test, time-frozen).
- [x] `afk` A mocked API response containing `bike`/`ski` results alongside `rower` results does
      not change any sensor's value (automated test).
- [x] `afk` `calories_total`, `stroke_count`, `stroke_rate`, and `drag_factor` appear as extra
      attributes on `last_workout_date` (automated test).
- [x] `afk` All four sensors report `unknown` when zero `rower` results exist (automated test).
- [x] `hitl` On the real HA instance, with a real logged rowing result, visually confirm all
      four sensors and the extra attributes show correct, sensible values in the HA UI.

---

## Phase 3: On-Demand & Scheduled Refresh

**Goals covered**: §6.4 (manual refresh), §6.6 (polling schedule).

### What to build

Add `button.py` exposing a refresh button that triggers an immediate coordinator refresh
on demand. Replace the Phase 1/2 setup-only fetch with the fixed local-time nightly trigger
from the architectural decisions (e.g. 3:00 AM), using HA's time-based trigger helpers rather
than a rolling interval, so the poll time is deterministic across restarts. Both the button and
the nightly trigger call the same coordinator refresh path built in Phase 1.

### Test approach

Automated: a test asserting the button's service call results in a new API fetch (mock call
count increments), and a time-travel test asserting the nightly trigger fires a refresh at the
configured local time without waiting in real time. Manual: pressing the real button after a
real row, and — because a scheduled trigger's *real* wall-clock firing can't be verified any
other way — leaving the instance running overnight at least once to confirm it actually fires at
the configured time in production.

### Acceptance criteria

- [x] `afk` Pressing the refresh button triggers an immediate coordinator refresh, verified by
      an incremented mock API call count (automated test).
- [x] `afk` The fixed nightly trigger fires a refresh at the configured local time (automated
      test using time-freezing/time-travel, not a real-time wait).
- [x] `hitl` On the real HA instance, press the dashboard refresh button after logging a new row
      and confirm the sensors update within a few seconds.
- [x] `hitl` Leave the integration running overnight at least once and confirm the nightly poll
      actually fires at the configured wall-clock time (via logs or an updated `last_updated`).

---

## Phase 4: Auth Resilience — Reauth & Options Flow

**Goals covered**: PRD Goal 2; §6.7 (reauth flow, options flow).

### What to build

Wire a 401 response from the coordinator's fetch into HA's standard reauth flow, prompting the
user to re-enter a token without losing the existing config entry/device/entities. Add an
options flow (Settings → Devices & Services → Concept2 Logbook → Configure) that lets the user
proactively rotate their token at any time, reusing the same validation logic built in Phase 1.

### Test approach

Automated: a test that forces a mocked 401 and asserts HA's reauth flow is initiated, plus a
follow-up asserting a valid token submitted through that flow resolves it. A separate test drives
the options flow end-to-end with a mocked valid token. Manual: this is the one behavior that
can't be fully trusted from mocks alone, since it depends on HA's real reauth notification
UX appearing correctly — worth one real confirmation with an actually-revoked token.

### Acceptance criteria

- [x] `afk` A simulated 401 triggers HA's reauth flow, and submitting a valid token through that
      flow resolves it, leaving the existing device/entities intact (automated test).
- [x] `afk` The options flow accepts a new token, validates it with the same logic as initial
      setup, and updates the config entry without removing/re-adding the integration (automated
      test).
- [ ] `hitl` On the real HA instance, revoke or regenerate the real Concept2 token so the next
      poll gets a real 401, and confirm the reauth prompt actually appears under Settings →
      Devices & Services.

---

## Phase 5: Poll Failure Handling — Repair Issues

**Goals covered**: §6.8 (error handling).

### What to build

Handle non-auth poll failures (timeout, 5xx, network error) by raising `UpdateFailed`
internally while sensors retain their last-known-good values, logging a warning, and retrying on
the next scheduled poll. Track consecutive failures across polls; after 3 in a row, raise a HA
repair issue. The counter resets and the repair issue clears on the next successful poll.

### Test approach

Automated: tests simulating 1, 2, and 3 consecutive mocked failures, asserting no repair issue
before the third and one present at/after the third, plus a test asserting a following success
clears it and resets the counter. Sensor-state assertions confirm last-known values persist
through failures. Manual: a real network-outage simulation against the live API, since that's
the only way to confirm HA's real Repairs UI surfaces the issue as expected.

### Acceptance criteria

- [ ] `afk` A single failed poll (mocked timeout/5xx) raises `UpdateFailed` while sensors retain
      their last-known values (automated test).
- [ ] `afk` After exactly 3 consecutive simulated failures, a HA repair issue is created; fewer
      than 3 does not create one (automated test).
- [ ] `afk` A successful poll following a raised repair issue clears it and resets the failure
      counter (automated test).
- [ ] `hitl` On the real HA instance, block network access to the Concept2 API for 3+ nightly
      polls and confirm a repair issue actually appears under Settings → Repairs.

---

## Phase 6: Diagnostics & Release Packaging

**Goals covered**: PRD Goals 3–4; §6.9 (diagnostics), §7 (installability/distribution), §10.

### What to build

Add `diagnostics.py` implementing HA's "Download Diagnostics" action, including coordinator
state and the last raw API response with the access token redacted. Finalize `hacs.json` and
confirm the repository installs correctly via HACS as a custom repository. Close out the release:
confirm the repo is public and MIT-licensed, bump `manifest.json`'s `version`, and push a
matching `v0.1.0` git tag.

### Test approach

Automated: a test asserting the token string is absent from the diagnostics payload while
coordinator state/last-response data is present. Manual: everything else in this phase is
inherently about the real distribution mechanism (HACS install UX, a real downloaded diagnostics
file, actual repo/license/tag state) and can't be meaningfully faked in a unit test.

### Acceptance criteria

- [ ] `afk` The diagnostics payload includes coordinator state and the last raw API response
      with the access token string absent/redacted (automated test).
- [ ] `afk` The full `pytest-homeassistant-custom-component` suite (Phases 1–6) passes.
- [ ] `hitl` On the real HA instance, use Download Diagnostics and manually inspect the file to
      confirm the token is redacted and nothing else sensitive leaks.
- [ ] `hitl` Add this repo as a HACS custom repository on the real HA instance and confirm it
      installs and updates correctly end-to-end.
- [ ] `hitl` Confirm the repo is public and MIT-licensed, then tag and push an initial `v0.1.0`
      release.
