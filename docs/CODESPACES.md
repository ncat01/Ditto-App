# Run Ditto in GitHub Codespaces

Repository: https://github.com/ncat01/Ditto-App

This is a connected sandbox test, not continuous production hosting. No database
API key is needed. Live Meta discovery, real outreach, LLM calls and manipulation
detection are still unavailable.

## Launch

1. In the repository, choose **Code → Codespaces → Create codespace on main**.
2. Wait for the dev container to install the Python dependencies. Its post-start
   command applies migrations and launches one API plus one follow-up scheduler.
3. In **Ports**, find **8010**. Copy its forwarded address. It looks like
   `https://YOUR-CODESPACE-8010.app.github.dev/`.
4. For phone access, right-click port **8010 → Port Visibility → Public**. The port
   is private by default. Only this test API becomes publicly reachable: Ditto
   still requires server sign-in for private records and media. Keep other ports
   private and do not put a GitHub token in the Android app.
5. Open the forwarded address with `/api/health` appended. It should show
   `database: connected` and describe the sandbox providers.

The forwarded URL uses HTTPS; uvicorn itself serves HTTP inside the container.
Leave the internal port protocol at HTTP. Changing it to HTTPS would require TLS
inside uvicorn and is unnecessary for the external HTTPS address.

If automatic startup did not complete, run from the repository root:

```bash
.venv/bin/python backend/scripts/codespaces.py start
```

Check `.ditto-data/backend.log` for startup errors. Logs do not intentionally print
tokens; do not publish account data or provider secrets. A rebuild recreates the
container but the workspace survives. A different/new Codespace has its own data.

## Connect Android

Install `DITTO-connected-test-debug.apk`. Log out of the offline demo if needed.
Choose **Connected test** and paste the backend root URL, including trailing `/`.
Create a separate server account with a password of at least 10 characters.
Offline device accounts are preserved and are not uploaded or migrated.

Connected mode starts with an empty account. In **Profile**, choose **Load server
sample cases** to explicitly seed that account's generated corpus. Then use
**Originals** to upload a real file (25 MB maximum), scan it, and review cases.
Unknown uploads have no invented matches. Approvals record sandbox receipts on
the server; repeated approvals are blocked. Other users cannot access the account's
records or private media. Refresh checks the server; data never silently switches
to the device's offline database.

Server tokens are encrypted using Android Keystore. They expire after seven days.
Logout clears the device token and attempts server revocation. If offline during
logout, an already issued server session lasts until its expiry. Tokens and media
are not embedded in the APK. Temporary playback media is kept in private app cache,
separated by server and user. Push notifications remain unavailable.

## Data and backups

SQLite: `.ditto-data/ditto.db`; private videos: `.ditto-data/media`.
These paths are ignored by Git and excluded from delivery archives.
Stopping/resuming the same Codespace preserves workspace files. Deleting that
Codespace deletes its database and uploads; it does not restore them from Git.
Take a consistent snapshot before deleting it:

```bash
.venv/bin/python backend/scripts/backup_sqlite.py .ditto-data/ditto.db .ditto-data/backups/ditto-001.db
```

Download that snapshot and a separate copy of `.ditto-data/media` to a private
location. Use a new backup filename each time. The script checks SQLite integrity;
it does not include videos or provide an offsite backup service.

## Limits

Codespaces consumes your included compute/storage allowance and stops when idle.
When stopped, API calls and scheduler checks do not run; resume it to continue.
Persisted deadlines are checked by the scheduler after it resumes. Check your
GitHub billing/usage page, keep overage spending disabled if you want no paid use,
and do not assume continuous availability. This configuration cannot make
Codespaces an always-on production server.

References: https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace
and https://docs.github.com/en/codespaces/about-codespaces/deep-dive.
