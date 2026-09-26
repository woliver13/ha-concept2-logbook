# PRD: Concept2 Logbook Home Assistant Integration

**Status:** Draft — ready for implementation
**Repo:** `ha-concept2-logbook` (public, MIT license)
**Last updated:** 2026-09-18

## 1. Summary

A Home Assistant custom integration (`custom_components/concept2/`) that pulls rowing workout
data from the Concept2 Logbook API and exposes it as HA sensors. It is one data source among
several in a larger personal automation project ("Second Brain"). Its primary purpose is to
answer, from within Home Assistant, "when did I last row, and how long ago was that?" so that a
separate downstream automation (out of scope here) can alert when the answer is "too long."

## 2. Background / Context

- Runs on Home Assistant OS (HAOS) with HACS already installed and working.
- Developer background is C# / clean architecture. Rough mapping for this project:
  `DataUpdateCoordinator` ≈ repository/data-access layer, `sensor.py` ≈ presentation layer,
  `config_flow.py` ≈ setup/DI wiring.
- Distinct from `doug-hoffman/ha-c2_pm5`, which connects directly to a PM5 monitor over
  Bluetooth for real-time data. This integration instead polls the cloud Logbook API for
  already-logged historical results. The repo name (`ha-concept2-logbook`) is chosen specifically
  to avoid that confusion.
- The Concept2 Logbook API personal access token is generated via log.concept2.com → Edit
  Profile → Applications (in the menu on the left) → Concept2 Logbook API → View Token.

## 3. Goals

1. Reliably surface "last workout" facts and a "days since last rowing workout" count inside
   Home Assistant, computed correctly across timezones and day boundaries.
2. Keep the access token out of version control entirely — it must never be hardcoded in
   `configuration.yaml` or any file that could be committed, even to a private repo.
3. Follow standard Home Assistant custom-integration conventions (config flow, coordinator,
   device classes, reauth, repair issues) closely enough that this integration could later be
   submitted to the HACS default store with minimal rework.
4. Ship as a working, installable, testable MVP without over-building for hypothetical future
   needs.

## 4. Non-Goals (MVP)

- No support for other Concept2 machine types beyond the indoor rower (`bike`, `ski` results are
  fetched by the API but explicitly filtered out of these sensors — see §6.2).
- No historical analytics (weekly/monthly totals, personal records, trend charts) — see the
  Roadmap's richer-sensors item (§8).
- No multi-profile / multi-user support in the UI or automations, though the data model is built
  so this isn't a breaking change later (see §6.7).
- No building of the actual "haven't rowed in N days" alert automation. This integration's
  responsibility ends at exposing an accurate sensor; the alert itself (thresholds, notification
  channel, wording) is a separate Second Brain automation, following the same
  sensor-exposes-data-only pattern already established elsewhere in that project.
- No touching of other data sources in the broader project — those are separate, already-working
  or separately-deferred pieces outside this repo's scope.
- No HACS default-store submission in this phase (see the Roadmap, §8).

## 5. Users

Single user (the developer), self-hosting HA for personal use. The repo is public so that other
Concept2 + Home Assistant users can install it via HACS as a custom repository, but there is no
current intent to actively support external users during the MVP phase.

## 6. Functional Requirements (MVP)

### 6.1 Files

- `manifest.json` — standard boilerplate; `iot_class: cloud_polling`.
- `config_flow.py` — token entry UI, live validation, reauth flow, options flow.
- `__init__.py` — sets up the `DataUpdateCoordinator`, registers the fixed-time nightly poll,
  registers the refresh button and diagnostics.
- `sensor.py` — the four sensor entities.
- `button.py` — the manual refresh button entity.
- `diagnostics.py` — HA "Download Diagnostics" support, token redacted.
- `strings.json` / `translations/en.json` — config flow / reauth / options flow copy.
- `hacs.json`, `README.md`, `LICENSE` (MIT) — for HACS custom-repository installability.

### 6.2 Data source

- `GET https://log.concept2.com/api/users/me/results` with `Authorization: Bearer <token>`.
- Fetch page 1 only (default `per_page`, assumed sorted by date descending — verify during
  implementation and explicitly sort/select client-side if the API does not guarantee this).
  MVP only needs the single most recent result; do not fetch or cache additional history pages.
  This is a deliberate scope cut — a future richer-sensors extension (§8) that needs more history
  should extend the coordinator's fetch logic then, not now.
- Filter results to `type == "rower"` before use. A logged bike or ski-erg session must not reset
  "days since last workout" or change the "last workout" sensors — the whole point of these
  sensors is tracking rowing specifically.
- The account's Concept2 user id (from the API response) is used as the config entry's
  `unique_id` and as the basis for entity `unique_id`s and the HA device identifier (see §6.7).

### 6.3 Sensors

All sensors belong to a single HA device representing the Concept2 account.

| Sensor | State | `device_class` | `state_class` | Unit | Notes |
|---|---|---|---|---|---|
| Last workout date | timestamp of most recent `rower` result | `timestamp` | — | — | |
| Last workout distance | distance of most recent `rower` result | `distance` | `measurement` | meters | Native API unit; no imperial conversion needed for rowing. |
| Last workout duration | duration of most recent `rower` result | `duration` | `measurement` | seconds | API's `time` field (tenths of a second) divided by 10. |
| Days since last workout | integer days between last `rower` result's date (converted to HA's local timezone) and today | — | `measurement` | days | See §6.5 for zero-result and timezone handling. |

Extra API fields not worth a dedicated MVP sensor — `calories_total`, `stroke_count`,
`stroke_rate`, `drag_factor` — are attached as `extra_state_attributes` on the **last workout
date** sensor, since the coordinator already has them in the same API response at no extra cost.
The `workout.splits` array is excluded (too large/nested for a state attribute; a future
richer-sensors concern, §8, if ever needed).

### 6.4 Manual refresh

A `button` entity ("Refresh Concept2 Data" or similar) triggers an immediate coordinator refresh
outside the nightly schedule, so the user can confirm a just-finished workout shows up without
waiting until the next scheduled poll.

### 6.5 Days-since-last-workout: edge cases

- **No `rower` results exist at all** (e.g. immediately after setup, before any workout is
  logged): all four sensors report HA's native `unknown` state. No sentinel values (`0`, `-1`,
  `999`) are invented.
- **Timezone handling**: the workout timestamp is converted to HA's configured local timezone
  (`hass.config.time_zone`) before computing the calendar-day difference from "now." This matters
  because a row finished late at night in local time must not be miscounted due to UTC rollover —
  the entire purpose of this sensor is an accurate day count for downstream alerting.
- A workout logged "today" (local time) → `days_since_last_workout == 0`.

### 6.6 Polling schedule

- Primary trigger: a fixed local time each night (e.g. 3:00 AM), using HA's time-based trigger
  helpers rather than a rolling `update_interval` timedelta. This is deliberate — a plain 24h
  interval drifts with HA restarts, making "days since last workout" less deterministic. A fixed
  nightly time keeps the computation anchored to a known point each day, consistent with this
  project's other nightly-polling data sources.
- Secondary trigger: the manual refresh button (§6.4).

### 6.7 Config flow, auth, and entity identity

- Single-step setup: user pastes their Concept2 personal access token into a masked (password-
  type) field.
- On submit, the config flow makes a live test API call (e.g. `GET /users/me`) to validate the
  token before creating the config entry. Distinguish `invalid_auth` (bad/expired token) from
  `cannot_connect` (network/API unreachable) in the error shown to the user.
- The config entry's `unique_id` is the Concept2 user id returned by that validation call. This
  prevents adding the same account twice and means the "multiple rowers" roadmap item
  (§8) is additive — each account gets its own config entry/device — rather than requiring a
  breaking migration.
- Entity `unique_id`s and the HA device identifier are namespaced by that same Concept2 user id
  (e.g. `concept2_<user_id>_days_since_workout`).
- **Reauth flow**: if the coordinator receives a 401 from the API, HA's standard reauth flow is
  triggered (a repair/notification prompts the user to re-enter a token), rather than the
  integration silently failing.
- **Options flow**: the user can also proactively rotate the token at any time via Settings →
  Devices & Services → Concept2 → Configure, reusing the same validation logic as initial setup.

### 6.8 Error handling (non-auth failures)

- A failed poll (timeout, 5xx, transient network issue) raises `UpdateFailed` internally, per
  standard coordinator behavior; sensors retain their last-known-good values rather than going
  blank, and the integration logs a warning and retries on the next scheduled poll.
- After **3 consecutive** failed nightly polls, the integration raises a Home Assistant repair
  issue, so a sustained outage becomes visible instead of silently feeding stale data into the
  downstream "days since last workout" alert. The counter resets on the next successful poll.

### 6.9 Diagnostics

`diagnostics.py` implements HA's "Download Diagnostics" action for the integration's config
entry, including coordinator state and the last raw API response, with the access token redacted.

## 7. Non-Functional Requirements

- **Security**: the access token is entered only via the config/options flow UI and stored in
  HA's encrypted config entry storage. It must never be written to `configuration.yaml`, logs, or
  any file that could be committed to the repo.
- **Testing**: MVP acceptance requires an automated unit test suite built on
  `pytest-homeassistant-custom-component`, covering:
  - config flow: valid token, invalid token (`invalid_auth`), unreachable API (`cannot_connect`),
    duplicate account (`unique_id` collision), reauth flow, options flow.
  - coordinator: correct parsing of a mocked API response, `rower`-type filtering, days-since
    calculation including timezone edge cases (late-night workout, midnight boundary, "today"),
    zero-results → `unknown`, and the 3-failure repair-issue threshold.
  - sensor: correct state/attributes/device_class per §6.3, including the `unknown` no-data case.
- **Installability**: installable via HACS as a custom repository (`hacs.json`, README with setup
  instructions, git tags for releases) — not just a manual file copy — matching the existing HACS
  workflow already in use on this HA instance.
- **Distribution**: public GitHub repo, MIT license (satisfies HACS default-store licensing
  requirements up front, ahead of any Phase 2 submission). Releases are cut manually: bump
  `manifest.json`'s `version` and push a matching semver git tag (e.g. `v0.1.0`) — no CI/release
  automation for MVP.

## 8. Roadmap (Post-MVP, not built now)

Named here to set expectations for what "future work" means on this project; none of the
following is in scope for MVP acceptance. These are intentionally *not* labeled "Phase N" — that
numbering is reserved for the MVP build-out phases in
[.plans/concept2-ha-integration.md](../.plans/concept2-ha-integration.md).

- **Richer sensors**: weekly/monthly distance and time totals, personal records,
  stroke rate/drag factor history — likely requires extending the coordinator to fetch and cache
  a rolling history window (§6.2) rather than just the latest result.
- **HACS default store submission**: pass `hassfest`/HACS validation, brands
  registration, CI validation workflow.
- **Multi-profile support**: multiple Concept2 accounts/rowers under one HA instance,
  if other household members start rowing. The user-id-keyed config entry/device design in §6.7
  is intended to make this additive rather than a breaking change.

## 9. Open Questions / Risks

- Whether `GET /users/me/results` is actually sorted by date descending by default needs to be
  confirmed against the live API during implementation; if not, client-side sorting/selection of
  the most recent `rower` result is required.
- Concept2 API rate limits are unknown but assumed generous enough for one nightly poll plus
  occasional manual refreshes; not expected to be an issue at this volume.
- No confirmation yet on whether the personal access token expires/rotates on Concept2's side —
  the reauth flow (§6.7) is the safety net regardless.

## 10. Acceptance Criteria (Definition of Done for MVP)

- [ ] Integration installs via HACS custom repository on the target HAOS instance.
- [ ] Config flow accepts a token, validates it live, and clearly distinguishes invalid-token vs.
      connection errors.
- [ ] All four sensors report correct values after a successful poll, with correct
      `device_class`/`state_class`/unit per §6.3.
- [ ] `days_since_last_workout` is correct across a local-timezone midnight boundary and reports
      `0` for a same-day workout.
- [ ] All sensors report `unknown` when zero `rower` results exist.
- [ ] Bike/ski-erg results do not affect any sensor's value.
- [ ] Manual refresh button triggers an immediate, verifiable data update.
- [ ] A simulated 401 triggers HA's reauth flow; re-entering a valid token resolves it.
- [ ] The Options flow allows token rotation without removing the integration.
- [ ] 3 consecutive simulated poll failures raise a repair issue; a subsequent success clears it.
- [ ] Diagnostics download includes coordinator state with the token redacted.
- [ ] Automated test suite (`pytest-homeassistant-custom-component`) passes, covering the cases
      listed in §7.
- [ ] Repo is public, MIT-licensed, and tagged with an initial release (e.g. `v0.1.0`).
