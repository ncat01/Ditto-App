# Commercial launch status

**Not deployed. Not ready for public commercial launch.** The Android download is a debug integration build. This applies to the full advertised detection, review, outreach and follow-up product.

## Implemented

- Account signup/login, expiring sessions, recovery, email verification, password-confirmed deletion and request limits.
- Per-user Instagram browser authorization, encrypted tokens, refresh, disconnect and own-media import. Live sign-in on a device remains unverified.
- Private Appwrite uploads and Instagram imports, owner-checked playback, failed-upload cleanup and durable account-deletion retries. Local copies are retained for hashing and backups.
- Measured image/video pHash comparison and consented Google web-image search. Search links are unverified leads; these features do not search all Instagram content or determine infringement.
- Signup tutorial using actual Ditto screenshots and an Instagram connection button.
- Non-root Docker deployment configuration, HTTPS proxy, backup/restore scripts and release signing gates.
- Production refuses sample scanning, sample evaluation/media, demo clock changes, simulated follow-ups and approvals without a live transport.

## Remaining work and dependencies

| Requirement | Current state | What closes it |
| --- | --- | --- |
| Durable hosted backend | SQLite/FastAPI remains active. Appwrite TablesDB is provisioned but inactive. | Implement/test the Appwrite metadata/authentication migration and Functions deployment, or provision an always-on host for the prepared persistent Docker backend. |
| Appwrite deployment access | The key is in Codespaces; this local session has no authenticated Appwrite management connection. The key lacks Functions deployment and schema creation scopes. | Operator-owned deployment access through a supported connection or private runner, after a deployable implementation exists. Do not paste a key in chat. |
| Public Instagram access | Secret/redirect configuration is checked; public-user access is not verified. | Live two-account device OAuth/import tests and applicable Meta review/approval. |
| Email delivery | Recovery/verification code exists; production SMTP is not supplied or verified. | Private SMTP configuration and real inbox tests, including expiry and session revocation. |
| Reverse search | Provider adapter, consent and cost limits exist; Google configuration/billing is pending. | Operator-approved provider configuration and live search/quota tests. |
| Live outreach/follow-up | No live message transport exists; production refuses dispatch. | Implement a permitted transport, delivery/audit/retry handling and end-to-end checks. |
| Public policies | Draft pages exist; support email is set. Operator identity and retention policy are missing. | Operator-specific identity, retention/backup policy and review of published documents. |
| Android distribution | Debug APK available; private release signing gates exist. | Owner-held keystore, stable backend origin, signed APK/AAB and device/store checks. |
| Operations | Docker/Caddy files and local backup tests exist. No production runtime is verified. | Hosted startup, monitoring, restore drill and Appwrite file retention/export checks. |

## Hosting constraint

The user's no-card requirement remains in effect. Appwrite TablesDB uses managed APIs rather than a SQLAlchemy connection. A Functions deployment needs durable request-scoped storage and asynchronous processing for slow video/provider work; copying SQLite into a Function is not a valid migration. Synchronous Functions have a 30-second limit: https://appwrite.io/docs/products/functions/execute .

Appwrite native PostgreSQL could preserve more of the existing ORM, but its documented setup requires a paid plan and payment method and starts at $10/month. Do not activate it under the current authorization: https://appwrite.io/docs/products/databases/postgresql .

## One development update

Use the batch in [DEPLOYMENT.md](DEPLOYMENT.md) to verify the updated Codespaces backend. This does not deploy a commercial service. Project creation, storage checks, passing tests and renaming the app do not close the requirements above.

## Signing

Set DITTO_SIGNING_STORE_FILE, DITTO_SIGNING_STORE_PASSWORD, DITTO_SIGNING_KEY_ALIAS and DITTO_SIGNING_KEY_PASSWORD privately. Build with `-PdittoApiBaseUrl=https://your-production-host/`. Debug signing is never a release fallback. The development docker-compose.yml enables demo mode and must not be used as the public deployment.
