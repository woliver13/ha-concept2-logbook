# Concept2 Logbook for Home Assistant

A Home Assistant custom integration that pulls your rowing workout history from the
[Concept2 Logbook API](https://log.concept2.com/) and exposes it as sensors — including a
"days since last workout" sensor for building your own "haven't rowed in a while" automation.

This integration talks to the **Concept2 Logbook cloud API** (your already-logged workout
history). It is not related to, and does not replace,
[`doug-hoffman/ha-c2_pm5`](https://github.com/doug-hoffman/ha-c2_pm5), which connects directly
to a PM5 monitor over Bluetooth for real-time, in-progress workout data.

## Features

- Polls your Concept2 Logbook account once nightly, by default at 3:00 AM (your Home Assistant local time), plus on demand via a refresh button. Change the nightly poll time under the integration's **Configure** option.
- Optionally polls more often than nightly: set **Also poll every N minutes** (minimum 15) under **Configure**. Leave it blank to keep nightly-only polling.
- Fires a `workout_logged` event for each newly logged rowing result, so automations can react
  to a new workout. Results that were already in your logbook when you set up the integration
  never fire.
- Only considers indoor **rower** results — bike and SkiErg entries in your logbook are ignored
  so they don't affect these sensors.
- Your access token is entered through Home Assistant's own setup UI and stored in HA's
  encrypted config entry storage. It is never written to YAML, logs, or this repo.

### Entities

| Entity | Description |
|---|---|
| `sensor.<name>_last_workout_date` | Timestamp of your most recent rowing result. Also carries `result_id`, `calories_total`, `stroke_count`, `stroke_rate`, `drag_factor`, and `heart_rate_avg` as extra attributes. |
| `sensor.<name>_last_workout_distance` | Distance (meters) of your most recent rowing result. |
| `sensor.<name>_last_workout_duration` | Duration (seconds) of your most recent rowing result. |
| `sensor.<name>_last_workout_pace` | Pace (seconds per 500 m) of your most recent rowing result. |
| `sensor.<name>_days_since_last_workout` | Whole days since your last rowing result, computed in your Home Assistant instance's local timezone. |
| `event.<name>_new_workout` | Fires a `workout_logged` event for each new rowing result, oldest first and at most 10 per poll. The event data carries `result_id`, `date`, `distance_meters`, `duration_seconds`, `pace_500m_seconds`, `calories_total`, `stroke_count`, `stroke_rate`, `drag_factor`, `heart_rate_avg`, and `heart_rate_ending`. |
| `button.<name>_refresh` | Triggers an immediate data refresh instead of waiting for the next scheduled poll. |

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
    triggers:
      - trigger: numeric_state
        entity_id: sensor.<name>_days_since_last_workout
        above: 3
    actions:
      - action: notify.notify
        data:
          message: "It's been a few days since your last row."
```

To react to a new workout instead, trigger on the event entity:

```yaml
automation:
  - alias: "Announce a new row"
    triggers:
      - trigger: state
        entity_id: event.<name>_new_workout
        not_from:
          - unavailable
          - unknown
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type == 'workout_logged' }}"
    actions:
      - action: notify.notify
        data:
          message: >-
            Logged {{ trigger.to_state.attributes.distance_meters }} m.
```

See [`docs/PRD-concept2-ha-integration.md`](docs/PRD-concept2-ha-integration.md) for the full
product spec, including planned future work (HACS default-store submission, richer historical
sensors, multi-account support).

## Contributing

Issues and pull requests are welcome. Please open an issue first for larger changes.

## License

[MIT](LICENSE)
