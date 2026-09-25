# Test the reauth prompt (Phase 4 HITL)

This procedure shows that Home Assistant asks for a new token when the Concept2 API rejects the old token.
You regenerate your real token on the Concept2 website. The old token stops working.
Home Assistant then shows the reauth prompt.

## Before you start

You need:

- Access to your Home Assistant instance with the Concept2 Logbook integration installed.
- The Phase 4 version of the integration files. The files must include the reauth flow.
- A Concept2 Logbook account that has a personal access token.

Time to complete: 10 minutes.

> **WARNING:** This procedure makes your old token invalid. Home Assistant stops getting data until you enter the new token.

## Procedure

### 1. Regenerate the token

1. Go to [log.concept2.com](https://log.concept2.com) and log in.
2. Select the user icon at the top right of the page.
3. Select **Edit Profile**.
4. In the menu on the left, select **Applications**.
5. Under **Concept2 Logbook API**, select **View Token**.
6. Select **Regenerate Token**.
7. Copy the new token.

### 2. Cause a failed update

1. Go to **Settings → Devices & Services → Concept2 Logbook**.
2. Select the **Refresh** button.

The Concept2 API rejects the old token with a 401 error.

### 3. Confirm the reauth prompt

1. Go to **Settings → Devices & Services**.
2. Find the **Concept2 Logbook** card.
3. Make sure the card shows **Reconfigure** or **Action needed**.

**Expected result:** The prompt appears. This is the result the acceptance criterion requires.

If the prompt does not appear, go to **Troubleshooting**.

### 4. Complete the reauth flow

1. Select **Reconfigure** on the Concept2 Logbook card.
2. Paste the new token.
3. Select **Submit**.
4. Make sure a message shows that Home Assistant updated the access token.

### 5. Confirm that nothing is lost

1. Go to **Settings → Devices & Services → Concept2 Logbook**.
2. Make sure the integration shows only one device.
3. Make sure the four sensors show values.
4. Select the **Refresh** button.
5. Make sure the sensors show correct values.
6. Make sure the "Action needed" message is gone.

**Expected result:** The device and sensors are the same as before the test.

### 6. Record the result

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
| No **Reconfigure** option appears | The installed files do not have the Phase 4 code | Copy the Phase 4 `custom_components/concept2` folder to Home Assistant. Restart Home Assistant. Select **Refresh** again. |
| The prompt does not appear after **Refresh** | Home Assistant did not restart after the file copy | Restart Home Assistant. Select **Refresh** again. |
| The form shows "Invalid or expired access token" | You did not copy the complete token | Copy the token again from the **Applications** page. |
| The form shows "different Concept2 account" | You entered a token for another account | Enter the token for the account that you used at setup. |

## Not tested here

You cannot test the wrong-account check by hand without a second account.
This check rejects a valid token from a different Concept2 account.
An automated test covers it: `tests/test_reauth.py::test_reauth_rejects_bad_tokens`.
