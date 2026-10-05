# Connected test and production next steps

SQLite is selected; no Supabase, Firebase or database API key is needed. Connected Android mode uses the authenticated FastAPI backend. Offline mode retains a separate device database.

## Launch the selected Codespaces environment

Source is published to https://github.com/ncat01/Ditto-App. Open **Code ? Codespaces ? Create codespace on main**, wait for setup, and make port **8010** public. Use the forwarded HTTPS URL in Android Connected test. See [the full guide](CODESPACES.md).

Git authorization does not include Codespaces API scope, so the initial Codespace must be launched through your GitHub account UI. Never paste a GitHub token into chat or the APK. Provider credentials have not been added.

## Before a production release

- Select an always-on host with persistent SQLite and media storage; Codespaces has idle shutdown and metered quotas.
- Back up SQLite with `backend/scripts/backup_sqlite.py`, back up media separately, and verify restoration.
- Add password recovery and the desired account verification flow.
- Implement and verify provider adapters before requesting their credentials, one at a time. Meta access requires appropriate developer permissions and user consent.
- Replace synthetic discovery and sandbox outreach only after real provider behavior is verified.
- Produce a release-signed Android package with a privately managed signing key.

Version 1.3.0-connected-test retains the off-white, charcoal, pink, peach, coral and sunrise-yellow design. Font redistribution licenses are in `font-licenses/`.
