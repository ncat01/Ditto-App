# Instagram Login connection check

Store the Instagram-generated token as the personal Codespaces secret
`META_ACCESS_TOKEN`, granting access only to `ncat01/Ditto-App`.
Stop and restart the Codespace to receive the new secret, then run:

```sh
git pull --ff-only
.venv/bin/python backend/scripts/check_instagram.py
```

This reads the authorized Creator profile and up to five own-post metadata records.
An empty list is normal for a new account. No credentials, username, media URL or
post contents are printed or saved by the check. Token/key errors are explicit.
`META_API_VERSION` defaults to `v25.0` and may be changed if necessary.

The adapter does not publish, message, search arbitrary Instagram reposts or import
videos into Ditto. It is currently available to backend scripts. Per-user OAuth,
encrypted token storage and account binding are required before exposing the
Instagram account to Android or shared API users. A deployment-wide token is not
made accessible to every Ditto account. Webhooks and app publishing are not needed
for this initial read-only tester check.

If Meta reports an expired token, regenerate it in the Instagram setup dashboard,
update the secret, and restart Codespaces. Never share it in chat or screenshots.

Meta reference: https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/.
