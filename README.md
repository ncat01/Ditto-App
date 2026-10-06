# Ditto - Content credit and evidence review

Version **1.7.0** prepares an Appwrite backend and Android account workflows for private staging. **Public deployment and commercial launch are not yet verified.**

The app supports account signup, guided onboarding, an Instagram connection button, authorized own-media import, private originals, measured image/video hash comparisons, evidence review and optional provider-assisted drafts/search. Explicit recipient/evidence confirmation is required for configured SMTP outreach; ambiguous sends are never automatically retried. Hash similarity does not establish infringement, and Ditto does not search all Instagram content.

Install `apk/DITTO-1.7.0-debug.apk` for validation (Android 8+; debug signed). Cloud account uses the configured backend; offline demo keeps separate device-local accounts and labelled examples. A commercial release requires the verified hosted origin and owner signing key.

- `android/`: Kotlin Compose UI, private sessions, resumable-upload protocol and actual media playback.
- `backend/cloud/`: private Appwrite TablesDB, durable asynchronous work and per-user provider integration.
- `backend/app/`: preserved FastAPI/SQLite development backend.
- `demo_data/`: generated examples, not real discovered infringement.

[Consolidated deployment](docs/COMMERCIAL-DEPLOYMENT.md) provides one staging batch, access scopes, migration, backup and guarded publication. [Launch status](docs/PRODUCTION-NEXT.md) separates implemented features from missing live evidence. [Cloud architecture](docs/APPWRITE-CLOUD.md) explains the isolated schema and private worker.

Validation: **137 backend tests and 38 Android unit tests** pass; the Android debug build succeeds. Dependency audit found no known advisories after pinned package updates. Cloud tests use mocks; live Functions, Meta authorization, SMTP delivery, migration/restore and real-device launch flows remain unverified. Prior user verification established private Appwrite image upload/deletion only.

Owner: Svarsha T. Support: svarsha.t@gmail.com. Provider credentials, databases, private uploads, encryption keys and signing keys are excluded from source bundles.

[Codespaces development setup](docs/CODESPACES.md), [Instagram integration](docs/INSTAGRAM_SIGN_IN.md), and [historical offline handoff](HANDOFF.md) remain available. Codespaces is a development environment, not the commercial host.
