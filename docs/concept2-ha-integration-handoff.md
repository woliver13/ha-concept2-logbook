# Handoff: Concept2 Logbook Home Assistant Integration

## Goal
Build a private Home Assistant custom integration (`custom_components/concept2/`) that pulls rowing workout data from the Concept2 Logbook API and exposes it as HA sensors. MVP is for personal use only — not publishing to the HACS default store (yet). Part of a larger personal automation project ("Second Brain").

## Environment
- Home Assistant OS (HAOS), a recent release
- Note: recent HA versions renamed "Add-ons" to "Apps" in the UI — don't be thrown off by either term in docs.
- HACS is already installed and working
- Config editing done via a browser-based editor mounted to the HA config folder
- Developer background: C# / clean architecture. Map HA integration concepts accordingly — DataUpdateCoordinator ≈ repository/data-access layer, sensor.py ≈ presentation layer, config_flow.py ≈ setup/DI wiring.

## API details (already verified working)
- Concept2 Logbook API, personal access token generated via: log.concept2.com → Edit Profile → Applications (in the menu on the left) → Concept2 Logbook API → View Token
- Base endpoint confirmed working: `GET https://log.concept2.com/api/users/me/results` with header `Authorization: Bearer <token>`
- Confirmed real response shape includes: `id`, `date`, `distance`, `time` (in tenths of a second, e.g. 12000 = 20:00.0), `type` (e.g. "rower"), `stroke_count`, `stroke_rate`, `calories_total`, `drag_factor`, and a `workout.splits` array with per-split detail.
- Pagination via `meta.pagination` (per_page defaults to 50).

## MVP scope decisions (already made — don't re-litigate)
- **Include `config_flow.py`.** The access token must be entered via HA's UI-based setup flow (Settings > Devices & Services > Add Integration), stored in HA's encrypted config entry storage — NOT hardcoded in `configuration.yaml` or anywhere else that could end up committed to the GitHub repo. This is a deliberate change from the original plan (which considered skipping config_flow) specifically to avoid any personal credential ever touching version control, even in a "private" repo.
- Four files needed: `manifest.json` (boilerplate), `config_flow.py` (token entry UI), `__init__.py` (coordinator — polls the API, caches results), `sensor.py` (exposes a small set of sensors).
- Suggested minimum sensors: last workout date, last workout distance, last workout duration, **days since last workout** (this last one is the one that actually matters — it's meant to feed a "haven't rowed in N days" alert in the broader Second Brain project, same pattern as the existing ResMed myAir integration's "missed a night" comparison sensor).
- Polling cadence: nightly is sufficient (matches the rest of this project's data-source polling pattern — see the overall build plan artifact from this project if useful context).

## Repo naming
Suggested repo name: **`ha-concept2-logbook`** — distinguishes it from the existing (different, Bluetooth-based, real-time) `doug-hoffman/ha-c2_pm5` integration, which connects directly to the PM5 over Bluetooth rather than the Logbook API. Don't confuse the two approaches.

## Known rough edges hit today (context, not necessarily relevant to this specific task)
- This HA instance's browser-based web terminal has a paste bug — pasting into it can restart the session. A native terminal app with SSH works fine and is preferred for any command-line work.
- HACS custom repository additions have occasionally thrown 401 errors from GitHub, generally traced to HACS's own stored GitHub token needing re-authentication (delete + re-add the HACS integration to force a fresh device-login flow).

## What's NOT needed for this task
- No need to touch other, unrelated data sources in the broader project — those are separate, already-working (or separately-deferred) pieces outside this repo's scope.
