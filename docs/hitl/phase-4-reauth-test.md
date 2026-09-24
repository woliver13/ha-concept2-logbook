# Test the reauth prompt (Phase 4 HITL)

This procedure shows that Home Assistant asks for a new token when the Concept2 API rejects the old token.
It uses a token with an extra character. You do not revoke your real token.
You do not need a second Concept2 account.

## Before you start

You need:

- Access to your Home Assistant OS instance with the Concept2 Logbook integration installed.
- Your real Concept2 access token.
- The Terminal & SSH add-on or the File editor add-on.

Time to complete: 10 minutes.

> **WARNING:** Do not edit `core.config_entries` while Home Assistant Core runs.
> Home Assistant overwrites your change when it stops.

## Procedure

### 1. Make a backup

1. Go to **Settings → System → Backups**.
2. Select **Create backup**.
3. Select **Create**.
4. Wait for the backup to finish.

### 2. Stop Home Assistant Core

1. Open the Terminal & SSH add-on.
2. Enter this command:

   ```bash
   ha core stop
   ```

3. Wait until the command finishes.

### 3. Break the token

1. Enter this command to make a copy of the file:

   ```bash
   cp /config/.storage/core.config_entries /config/.storage/core.config_entries.bak
   ```

2. Open `/config/.storage/core.config_entries` in an editor.
3. Find the entry that has `"domain": "concept2"`.
4. Find the line `"access_token"` in that entry.
5. Add the letter `x` at the end of the token value, before the closing quotation mark.
6. Save the file.

Example: change `"access_token": "abc123"` to `"access_token": "abc123x"`.

### 4. Start Home Assistant Core

1. Enter this command:

   ```bash
   ha core start
   ```

2. Wait 2 minutes for Home Assistant to start.

### 5. Confirm the reauth prompt

1. Go to **Settings → Devices & Services**.
2. Find the **Concept2 Logbook** card.
3. Make sure the card shows **Reconfigure** or **Action needed**.
4. Make sure the notification list shows a message that asks you to reauthenticate.

**Expected result:** The prompt appears. This is the result the acceptance criterion requires.

If the prompt does not appear, go to **Troubleshooting**.

### 6. Complete the reauth flow

1. Select **Reconfigure** on the Concept2 Logbook card.
2. Enter your real Concept2 access token.
3. Select **Submit**.
4. Make sure a message shows that Home Assistant updated the access token.

### 7. Confirm that nothing is lost

1. Go to **Settings → Devices & Services → Concept2 Logbook**.
2. Make sure the integration shows only one device.
3. Make sure the four sensors are present.
4. Select the **Refresh** button.
5. Make sure the sensors show correct values.
6. Make sure the "Action needed" message is gone.

**Expected result:** The device and sensors are the same as before the test.

### 8. Record the result

1. Open `.plans/concept2-ha-integration.md` in this repository.
2. Find the Phase 4 item that starts with "On the real HA instance, revoke or regenerate".
3. Change `[ ]` to `[x]`.
4. Commit the change.

## Optional: test a token change from the options flow

1. Go to **Settings → Devices & Services → Concept2 Logbook**.
2. Select **Configure**.
3. Enter a token that ends with `x`.
4. Select **Submit**.
5. Make sure the form shows the error "Invalid or expired access token."
6. Enter your real token.
7. Select **Submit**.
8. Make sure the form closes with no error.

**Expected result:** The integration rejects the wrong token and keeps the old token.

## Troubleshooting

| Problem | Cause | Action |
|---|---|---|
| No prompt appears | The edit did not save, or Home Assistant was running during the edit | Repeat steps 2 to 4. |
| The integration does not load and shows no prompt | The JSON file is not valid | Copy `core.config_entries.bak` over `core.config_entries`. Repeat from step 3. |
| The form shows "different Concept2 account" | You entered a token for another account | Enter the token for the account that you used at setup. |
| Home Assistant does not start | The JSON file is not valid | Copy `core.config_entries.bak` over `core.config_entries`. Then enter `ha core start`. |

## Restore the original file

If you must undo the test, do these steps:

1. Enter `ha core stop`.
2. Enter this command:

   ```bash
   cp /config/.storage/core.config_entries.bak /config/.storage/core.config_entries
   ```

3. Enter `ha core start`.

## Not tested here

You cannot test the wrong-account check by hand without a second account.
This check rejects a valid token from a different Concept2 account.
An automated test covers it: `tests/test_reauth.py::test_reauth_rejects_bad_tokens`.
