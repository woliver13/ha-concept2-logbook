# Concept2 Logbook for Home Assistant

A Home Assistant custom integration that pulls your rowing workout history from the
[Concept2 Logbook API](https://log.concept2.com/) and exposes it as sensors — including a
"days since last workout" sensor for building your own "haven't rowed in a while" automation.

This integration talks to the **Concept2 Logbook cloud API** (your already-logged workout
history). It is not related to, and does not replace,
[`doug-hoffman/ha-c2_pm5`](https://github.com/doug-hoffman/ha-c2_pm5), which connects directly
to a PM5 monitor over Bluetooth for real-time, in-progress workout data.

## Features

- Polls your Concept2 Logbook account once nightly at 3:00 AM (your Home Assistant local time), plus on demand via a refresh button.
- Only considers indoor **rower** results — bike and SkiErg entries in your logbook are ignored
  so they don't affect these sensors.
- Your access token is entered through Home Assistant's own setup UI and stored in HA's
  encrypted config entry storage. It is never written to YAML, logs, or this repo.

### Entities

| Entity | Description |
|---|---|
| `sensor.<name>_last_workout_date` | Timestamp of your most recent rowing result. Also carries `calories_total`, `stroke_count`, `stroke_rate`, and `drag_factor` as extra attributes. |
| `sensor.<name>_last_workout_distance` | Distance (meters) of your most recent rowing result. |
| `sensor.<name>_last_workout_duration` | Duration (seconds) of your most recent rowing result. |
| `sensor.<name>_days_since_last_workout` | Whole days since your last rowing result, computed in your Home Assistant instance's local timezone. |
| `button.<name>_refresh` | Triggers an immediate data refresh instead of waiting for the nightly poll. |

If you haven't logged a rowing result yet, these sensors report `unknown` until you have.

## Requirements

- A Concept2 Logbook account with at least one logged rowing result.
- A personal access token: log in at [log.concept2.com](https://log.concept2.com) → **Edit
  Profile** → **Applications** (in the menu on the left) → **Concept2 Logbook API** → **View
  Token**. See [Get, replace, or revoke your Concept2 access token](docs/concept2-api-token.md).
- Home Assistant Core, recent enough to support standard config flow / reauth / repair issue
  APIs (developed against 2026.9.x).

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS → ⋮ → Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Find **Concept2 Logbook** in HACS and install it.
4. Restart Home Assistant.

### Manual

1. Copy the `custom_components/concept2` folder from this repo into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

Configuration is done entirely through the UI — there is no YAML setup.

1. Go to **Settings → Devices & Services → Add Integration** and search for **Concept2
   Logbook**.
2. Paste in your personal access token (see [Requirements](#requirements)).
3. The integration validates the token immediately and creates a device with the entities
   listed above.

If your token stops working later, Home Assistant will prompt you to re-authenticate. You can
also proactively rotate your token at any time from **Settings → Devices & Services → Concept2
Logbook → Configure**.

### Troubleshooting

If the nightly poll fails repeatedly (e.g. a Concept2 API outage), Home Assistant will raise a
repair issue after 3 consecutive failed attempts rather than silently going stale. Sensors keep
their last-known values in the meantime.

For deeper troubleshooting, use **Settings → Devices & Services → Concept2 Logbook → Download
Diagnostics** — your token is redacted from the output.

## Out of scope

This integration exposes data; it does not decide when to alert you. If you want a "you haven't
rowed in N days" notification, build a Home Assistant automation against
`sensor.<name>_days_since_last_workout` yourself — for example:

```yaml
automation:
  - alias: "Nudge me to row"
    trigger:
      - platform: numeric_state
        entity_id: sensor.<name>_days_since_last_workout
        above: 3
    action:
      - service: notify.notify
        data:
          message: "It's been a few days since your last row."
```

See [`docs/PRD-concept2-ha-integration.md`](docs/PRD-concept2-ha-integration.md) for the full
product spec, including planned future work (HACS default-store submission, richer historical
sensors, multi-account support).

## Contributing

This is a personal project built primarily for one household's Home Assistant setup, but issues
and pull requests are welcome.

## License

[MIT](LICENSE)
