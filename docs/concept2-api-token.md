# Get, replace, or revoke your Concept2 access token

This document tells you how to get the personal access token that the Concept2 Logbook integration uses.
It also tells you how to replace the token and how to revoke the token.

Time to complete: 5 minutes.

> **WARNING:** Keep your token secret. Anyone who has your token can read your Concept2 Logbook data.
> Do not post your token in a public place. Do not put your token in a file in a Git repository.

## Before you start

You need:

- A Concept2 Logbook account.
- Access to your Home Assistant instance.

## Get your token

1. Go to [log.concept2.com](https://log.concept2.com) and log in.
2. Select the user icon at the top right of the page.
3. Select **Edit Profile**.
4. In the menu on the left, select **Applications**.
5. Find **Concept2 Logbook API** under **Connected**.
6. Select **View Token**.
7. Copy the token.

<!-- VERIFY: If no token exists yet, the Applications page shows Concept2 Logbook API under "Connect" with a "Connect to Concept2 Logbook API" button. Confirm the name and add a step. -->

Now enter the token in Home Assistant:

1. Go to **Settings → Devices & Services**.
2. Select **Add Integration**.
3. Search for **Concept2 Logbook**.
4. Paste the token.
5. Select **Submit**.

## Replace your token

Do this when you think that someone else has your token. You can also do this to rotate your token on a schedule.

1. Do the steps in **Get your token** until you see the token.
2. Select **Regenerate Token**.
3. Copy the new token.

<!-- VERIFY: Does the page ask you to confirm? Does the old token stop working at once? Does the new token show on the same page? -->

The old token does not work after you replace it.
Home Assistant asks for the new token at the next data update.
To give the new token to Home Assistant now, do the steps in **Give the new token to Home Assistant**.

## Revoke your token

Do this when you no longer use the integration.

1. Do the steps in **Get your token** until you see the token.
2. Select **Revoke**.

The integration stops working. Home Assistant asks for a new token at the next data update.
To use the integration again, get a new token.

<!-- VERIFY: What does the page show after Revoke? Is there a "Connect to Concept2 Logbook API" button to make a new token? -->

## Give the new token to Home Assistant

### Use the reauth prompt

1. Go to **Settings → Devices & Services**.
2. Find the **Concept2 Logbook** card.
3. Select **Reconfigure**.
4. Paste the new token.
5. Select **Submit**.

The prompt shows after the next data update. To cause the update now, select the **Refresh** button of the integration.

### Use the options flow

Use this method when the prompt does not show.

1. Go to **Settings → Devices & Services → Concept2 Logbook**.
2. Select **Configure**.
3. Paste the new token.
4. Select **Submit**.

If the form shows "Invalid or expired access token," you did not copy the complete token. Copy the token again.

## Troubleshooting

| Problem | Cause | Action |
|---|---|---|
| You cannot find **Applications** | The page is narrow, or you are not on **Edit Profile** | Select **Edit Profile** from the user icon. Look for **Applications** in the menu on the left. |
| The form shows "Invalid or expired access token" | The token is not complete, or Concept2 replaced or revoked it | Copy the token again from the **Applications** page. |
| The form shows "different Concept2 account" | The token is for a different Concept2 account | Log in to the account that you used at setup. Copy the token from that account. |
