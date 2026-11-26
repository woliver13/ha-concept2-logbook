# Plan: New-Workout Events for the Concept2 Logbook Integration

> Source PRD: [docs/PRD-new-workout-events.md](../docs/PRD-new-workout-events.md)

## Architectural decisions

Durable decisions that apply across all phases:

- **Event entity**: `event.<device_name>_new_workout`, unique id
  `concept2_<user_id>_new_workout`, single event type `workout_logged`. Lives alongside
  `sensor.py`/`button.py` as a new `event.py` platform module, added to `PLATFORMS` in
  `__init__.py`.
- **Event payload fields**: `result_id`, `date`, `distance_meters`, `duration_seconds`,
  `pace_500m_seconds`, `calories_total`, `stroke_count`, `stroke_rate`, `drag_factor`, plus
  heart-rate summary fields when present. Exact source field names are verified against the
  live API during Phase 1/2 implementation (PRD §9); this list is the contract, not the API
  shape.
- **Coordinator data shape**: `Concept2DataUpdateCoordinator.data` changes from a single
  `Concept2Result | None` to a small result bundle exposing `latest: Concept2Result | None`
  (for existing sensors, unchanged behavior) and `new_results: list[Concept2Result]` (newly
  detected since the last successful poll, ascending by date, already flood-capped). Existing
  sensors are updated to read `.latest` instead of the coordinator data directly.
- **Seen-result persistence**: `homeassistant.helpers.storage.Store` (version 1), one store per
  config entry, holding a bounded list of the most recent 50 seen `result_id`s. Chosen over a
  single "highest id" or "latest date" watermark because a back-dated manual entry can arrive
  with a new id and an older date (PRD §6.2).
- **First-run baseline**: on first setup (empty store), every result from the first fetch is
  recorded as seen and none are treated as "new" — `new_results` is empty on that poll.
- **Flood guard**: at most 10 events fired per poll (`FLOOD_GUARD_MAX_EVENTS_PER_POLL`). Results
  beyond the cap are still marked seen and logged at warning level, never fired later.
- **Failure safety**: a failed poll (`UpdateFailed`) never writes to the seen-id store, so a
  result is never lost to a transient outage — it's picked up as "new" on the next success. This
  reuses the existing failure/repair-issue path from the MVP (coordinator.py).
- **Polling model**: the existing fixed nightly trigger is unchanged. A new optional
  options-flow field (`CONF_POLL_INTERVAL_MINUTES`) adds a second, independent
  `async_track_time_interval` trigger calling the same coordinator refresh path, registered only
  when set. Default is unset (off), so upgraded installs behave identically until a user opts in.
- **Test stack**: unchanged from the MVP plan (`pytest-homeassistant-custom-component`, mocked
  API, time-freezing for schedule/interval logic). Storage persistence is exercised via the test
  harness's `hass_storage` fixture rather than real disk I/O. Anything requiring the real HAOS
  instance or a real Concept2 account is called out per phase as `hitl`.

---

## Phase 1: Multi-Result Fetching (API & Coordinator)

**Goals covered**: PRD Goal 3 (never lose a result between polls); §6.3 (fetching more than the
latest result).

### What to build

Extend `Concept2ApiClient` with a method returning the list of recent `rower` results (filtered,
parsed, sorted ascending by date) instead of only the single newest one. Verify against the live
API docs/response whether `/users/me/results` supports date filtering or pagination (PRD §9); if
not, fall back to page 1 only, on the assumption a user logs far fewer results than a page holds
between polls. Update the coordinator to fetch this list each poll and expose it as
`new_results`-ready raw data, while the existing `.latest`-derived sensors keep their current
values and behavior unchanged. No event firing yet — this phase is pure plumbing that Phase 2
builds on.

### Test approach

Automated: API-client tests asserting multiple `rower` results are parsed and returned in
ascending date order, bike/ski-erg results are filtered out of the list (not just the single
latest), and existing single-result behavior (sensor values, `unknown` when empty) is unchanged.
Manual: none required — this phase has no new user-visible surface.

### Acceptance criteria

- [ ] `afk` The API client returns all `rower` results from the fetched page, sorted ascending
      by date, with bike/ski-erg results excluded (mocked API, automated test).
- [ ] `afk` Existing sensors (`last_workout_date`, distance, duration, days-since) report the
      same values as before this change when derived from the newest result in the list
      (regression test against the existing MVP test suite).

### Dependencies

- None. Builds on the already-merged MVP coordinator/API code.

---

## Phase 2: New-Result Detection, Persisted Baseline & `workout_logged` Event

**Goals covered**: PRD Goals 1, 2, 3, 5; §6.1 (event entity), §6.2 (detecting new results), §6.6
(failure behavior).

### What to build

Add the per-entry `Store`-backed seen-id set and the detection logic described in the
architectural decisions above: first-run baseline, ascending-order firing, flood guard, and
failure-safe (never mark-seen on a failed poll). Add `event.py` exposing one `event` entity per
config entry that fires `workout_logged` with the full payload (§6.1) once per newly detected
result, in ascending date order. Wire detection into the coordinator so both the nightly trigger
and the manual refresh button go through the same path.

### Test approach

Automated: first-run records a baseline and fires nothing; one new result fires one event with
the full payload; two new results between polls fire two events, oldest first; a simulated HA
restart with persisted state does not re-fire; a lost/corrupted store falls back to baseline
behavior; a back-dated result (new id, older date) still fires exactly once; bike/ski results
never fire; the flood guard caps events per poll and marks the remainder seen without firing;
a failed poll marks nothing as seen and the next successful poll fires the missed result(s).
Manual: none required — a logged row on the real account is a stretch confirmation, not a gate,
since every behavior above is reachable with a mocked API and the storage test fixture.

### Acceptance criteria

- [ ] `afk` First setup with no stored state records a baseline and fires zero events for
      existing history.
- [ ] `afk` A newly logged `rower` result fires exactly one `workout_logged` event with the
      payload fields from §6.1 (mocked API, automated test).
- [ ] `afk` Two results logged between polls fire two events, oldest first.
- [ ] `afk` A simulated HA restart with persisted seen-state does not re-fire already-seen
      results.
- [ ] `afk` A back-dated manual entry (new id, older date) fires exactly once.
- [ ] `afk` Bike and ski-erg results never fire, even when mixed in with new rower results.
- [ ] `afk` A failed poll marks nothing as seen; the next successful poll fires the result(s)
      that were missed.
- [ ] `afk` A lost/corrupted stored state falls back to baseline behavior instead of re-firing
      history.
- [ ] `afk` More new results than the flood-guard cap in a single poll fire only up to the cap;
      the rest are marked seen (not fired later) and logged at warning level.
- [ ] `hitl` On the real HA instance, log a real row, trigger a refresh, and confirm the event
      entity fires in Settings → Automations → "Add Automation" → trigger picker, with the
      expected payload visible in the event's attributes.

### Dependencies

- Builds on Phase 1 (needs the list of recent results, not just the latest).

---

## Phase 3: `result_id` Attribute & `last_workout_pace` Sensor

**Goals covered**: §6.4 (sensor additions).

### What to build

Expose `result_id` as an `extra_state_attributes` entry on `Concept2LastWorkoutDateSensor`. Add
a new `last_workout_pace` sensor reporting seconds per 500 m, derived as
`duration_seconds / (distance_meters / 500)`, with a zero-distance guard returning `None` rather
than dividing by zero. Heart-rate average, if present on a result, is exposed as an attribute,
not a new sensor, matching the existing attribute pattern on the date sensor.

### Test approach

Automated: a test asserting `result_id` appears in the date sensor's attributes; pace-sensor
tests for a normal result, a zero-distance result (guard returns `None`/`unknown`), and the
`unknown` state when there's no result yet. Manual: none required.

### Acceptance criteria

- [ ] `afk` `result_id` is present in the last-workout-date sensor's `extra_state_attributes`
      and matches the underlying result's id.
- [ ] `afk` `last_workout_pace` reports the correct seconds-per-500m value for a normal result.
- [ ] `afk` `last_workout_pace` reports `unknown` (not a division error) for a zero-distance
      result or when there's no result yet.

### Dependencies

- None beyond the existing MVP `Concept2Result` fields. Can be built independently of Phases 1–2.

---

## Phase 4: Configurable Sub-Daily Polling Interval

**Goals covered**: §6.5 (polling options).

### What to build

Add an optional options-flow field for polling every N minutes, in addition to the existing fixed
nightly trigger. Register a second `async_track_time_interval` trigger (only when the option is
set) that calls the same coordinator refresh path as the nightly trigger and the manual button,
so new-result detection (Phase 2) runs on every poll regardless of what triggered it. Leave the
field unset by default so every upgraded install keeps today's nightly-only behavior unless the
user opts in. Choose and document a sane minimum interval (PRD §9 flags Concept2 rate limits as
an open question to resolve during implementation — e.g. 15 minutes).

### Test approach

Automated: a time-freezing test asserting the interval trigger fires a refresh at the configured
cadence when set, and asserting no extra trigger is registered when the option is left unset
(regression check that existing nightly-only installs are unaffected). Options-flow validation
test for the minimum-interval bound. Manual: leaving the real instance running with the option
enabled to confirm the interval trigger actually fires in production, same as the existing
nightly-trigger manual check from the MVP plan.

### Acceptance criteria

- [ ] `afk` With the interval option unset, only the existing nightly trigger is registered
      (no behavior change for existing installs).
- [ ] `afk` With the interval option set, a refresh fires at the configured cadence
      (time-freezing test), going through the same detection/event path as Phase 2.
- [ ] `afk` The options-flow schema rejects an interval below the chosen minimum.
- [ ] `hitl` On the real HA instance, enable the interval option and confirm (via logs or
      `last_updated`) that polls actually happen at the configured cadence over a real time
      span.

### Dependencies

- None beyond the existing nightly-trigger/options-flow code from the MVP. Independent of
  Phases 1–3, though it increases how often Phase 2's detection logic runs.
