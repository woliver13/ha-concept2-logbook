# PRD: New-Workout Events for the Concept2 Logbook Integration

**Status:** Draft — for later (not yet scheduled)
**Repo:** `ha-concept2-logbook` (public, MIT license)
**Last updated:** 2026-11-26
**Builds on:** [PRD-concept2-ha-integration.md](PRD-concept2-ha-integration.md) (the MVP)

## 1. Summary

Make the integration announce each newly logged rowing result so that any Home Assistant user
can build automations on it (log it to a spreadsheet, send a notification, update a dashboard).
The integration publishes the fact "a new workout was logged" and knows nothing about who
listens. This turns the integration from "what was my last row?" (state) into "a row just
happened" (event), which is what most downstream automations need.

## 2. Background / Context

- The MVP exposes only the single most recent `rower` result as sensor state, polled nightly at
  a fixed local time plus a manual refresh button.
- State-only has three gaps for logging use cases:
  1. **No stable identity.** The coordinator holds `result_id` but nothing exposes it, so a
     consumer cannot tell whether it has already processed a result.
  2. **Latest-only.** Two results logged between polls lose the earlier one.
  3. **Latency.** A row finished in the morning is invisible until the next 3:00 AM poll (or a
     manual refresh).
- The repo is intended to reach other users (HACS default store, per the MVP PRD's roadmap), so
  the design must stay free of any one household's setup.

## 3. Goals

1. Fire exactly one HA event per newly logged `rower` result, with a payload useful to any
   consumer.
2. Never fire for results that existed before the integration was set up, and never fire twice
   for the same result (including across HA restarts).
3. Never lose a result because two were logged between polls.
4. Let users poll more often than nightly without changing the safe default.
5. Stay consumer-agnostic: no spreadsheet, notification, or other third-party logic in this repo.

## 4. Non-Goals

- No writing to Google Sheets, notification services, or any other destination. Consumers are
  user automations (an optional example blueprint is a stretch item, §8).
- No support for bike or ski-erg results (same filter as the MVP).
- No historical analytics, totals, or personal records (separate roadmap item in the MVP PRD).
- No real-time or in-progress workout data; that is the PM5 Bluetooth integrations' territory.
- No MQTT or other external pub/sub. The HA event bus is the pub/sub.

## 5. Users

Any Home Assistant user with a Concept2 Logbook account who wants automations triggered by a
completed row. The author is the first consumer, but the author's own automation lives outside
this repo.

## 6. Functional Requirements

### 6.1 Event entity

- Add an `event` platform entity per config entry, e.g. `event.<name>_new_workout`, with one
  event type (`workout_logged`).
- Each firing carries these attributes (source field names to be verified against the live API,
  see §9): `result_id`, `date` (local-timezone-aware), `distance_meters`, `duration_seconds`,
  `pace_500m_seconds` (derived: `duration / (distance / 500)`), `calories_total`,
  `stroke_count`, `stroke_rate`, `drag_factor`, and heart rate summary values when the result
  has them.
- Users can trigger automations from the event entity in the UI without knowing any event names.
- Optionally also fire the same payload on the HA event bus as `concept2_new_workout` for users
  who prefer bus events. Decide during implementation whether this is worth the extra surface
  area (§9).

### 6.2 Detecting new results

- Persist the set of recently seen result ids per config entry using HA's storage helper, so
  state survives restarts. Use a bounded set (for example the most recent 50 ids), not a single
  highest id or latest date, because a back-dated manual entry gets a new id with an older date.
- **First run baseline:** on first setup (no stored state), mark every result returned by the
  first fetch as seen and fire nothing. Old history must never flood automations.
- **Each poll:** fetch recent results, keep `rower` results whose id is not in the seen set, fire
  one event per new result in ascending date order, then add the ids to the seen set.
- **Flood guard:** cap events fired per poll (for example 10). Anything beyond the cap is marked
  seen and logged at warning level, not fired.
- If the stored state is lost or corrupted, fall back to the baseline behavior rather than
  re-firing history.

### 6.3 Fetching more than the latest result

- The coordinator currently fetches page 1 and keeps one result (MVP PRD §6.2 flagged this as a
  deliberate scope cut to extend later). Extend it to return the list of recent `rower` results.
- Prefer a date-filtered request if the API supports it; otherwise page 1 only, on the
  assumption that a user logs far fewer results than a page holds between polls. Verify (§9).
- The existing sensors keep working unchanged, derived from the newest result in the list.

### 6.4 Sensor additions (small, generic)

- Expose `result_id` as an attribute on the last-workout-date sensor.
- Add a `last_workout_pace` sensor (seconds per 500 m, derived) since pace is how rowers read
  their results. Heart rate average is an attribute, not a sensor, when present.

### 6.5 Polling options

- Keep the fixed nightly poll (default 3:00 AM local) exactly as today.
- Add an optional options-flow setting to also poll every N minutes (minimum to be decided
  against Concept2's rate limits, for example 15). Default is off, so existing installs behave
  identically after upgrading.
- The manual refresh button keeps working and runs the same new-result detection.

### 6.6 Failure behavior

- Poll failures follow the MVP rules (keep last-known state, repair issue after 3 consecutive
  failures). A failed poll must not mark anything as seen, so nothing is lost; the next
  successful poll picks the results up.

## 7. Non-Functional Requirements

- **Idempotency contract (documented in README):** consumers should treat `result_id` as the
  idempotency key. The integration guarantees at-least-once-per-result in normal operation and
  never duplicates across restarts, but consumers should still dedupe on `result_id`.
- **Privacy:** no change to token handling. Event payloads contain workout data only.
- **Backward compatibility:** existing entities, unique ids, and the nightly default are
  unchanged. Version bump follows the repo's patch/minor convention.
- **Testing** (`pytest-homeassistant-custom-component`):
  - first run fires nothing and records a baseline.
  - one new result fires one event with the full payload.
  - two new results between polls fire two events, oldest first.
  - restart with persisted state does not re-fire.
  - lost or corrupted stored state falls back to baseline.
  - back-dated result with a new id and an older date still fires once.
  - bike/ski results never fire.
  - flood guard caps firing and marks the rest seen.
  - failed poll marks nothing as seen; next success fires the missed result.
  - pace derivation, including zero-distance guard.

## 8. Roadmap / Stretch (not in this PRD's acceptance)

- Example blueprint in `docs/`: "append each new workout to a sheet," taking the sheet and
  worksheet as inputs, to demonstrate the consumer pattern without coupling the integration to
  any schema.
- Optional extra event types (for example `personal_best`) once richer history exists.

## 9. Open Questions / Risks

- Which result fields the API actually returns (heart rate shape, calories, stroke data) and
  their exact names. Verify against the live API and the Logbook API docs before coding.
- Whether `/users/me/results` supports date filtering or pagination parameters, and the default
  page size and sort order (the MVP PRD already flags sort order).
- Concept2 API rate limits for sub-daily polling; choose the minimum interval accordingly.
- Event entity versus bus event: whether to ship both, or the entity only.
- Whether editing or deleting a result in the Logbook after it fired should do anything. Current
  position: no, ignore.
- Timestamp timezone: the API gives no timezone, so results are interpreted in HA's local
  timezone (existing behavior); confirm this stays correct for users whose rower is in a
  different timezone than their HA.

## 10. Acceptance Criteria

- [ ] First setup records a baseline and fires no events for existing history.
- [ ] A newly logged rower result fires exactly one `workout_logged` event with the payload in
      §6.1.
- [ ] Two results logged between polls fire two events, oldest first.
- [ ] HA restart does not re-fire already-seen results.
- [ ] A back-dated manual entry fires once.
- [ ] Bike and ski-erg results never fire.
- [ ] A failed poll loses nothing; the next successful poll fires the missed results.
- [ ] `result_id` and pace are exposed per §6.4.
- [ ] Optional every-N-minutes polling works from the options flow and is off by default.
- [ ] Existing sensors, unique ids, and the nightly default are unchanged.
- [ ] Automated tests listed in §7 pass.
- [ ] README documents the event, its payload, and the `result_id` idempotency contract.
