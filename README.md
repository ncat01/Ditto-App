# Ditto ? An Agentic AI Content Credit System

Version **1.3.0-connected-test** adds a connected Android sandbox to the existing Kotlin Compose app and FastAPI backend, with a pink sunrise/sunset interface, bundled fonts and a new quotation-shaped logo.

Install `apk/DITTO-connected-test-debug.apk` (Android 8+; debug signed). Choose **Connected test** at sign-in and enter your backend HTTPS URL, or use **Offline demo** for device-local accounts. Connected mode supports server accounts, SQLite storage, private video uploads/playback, scans, approvals and follow-ups. Accounts in the two modes are separate.

Start with [Codespaces setup](docs/CODESPACES.md). The repository includes automatic backend setup in `.devcontainer/`. SQLite requires no database API key. Codespaces is a development environment with idle shutdown and usage quotas; this delivery is a connected test rather than an always-on production deployment.

Discovery uses generated demo assets and outreach is sandboxed. Live Meta discovery/messaging, LLM providers, face embeddings and ASR are not connected. No provider credentials, account databases or private uploads are included in source.

- `android/`: Kotlin, Compose, Room and encrypted server sessions.
- `backend/`: FastAPI, SQLAlchemy, Alembic and account-scoped authenticated APIs.
- `demo_data/`: generated video manifest and matcher evaluation.
- [Next production steps](docs/PRODUCTION-NEXT.md).
- [Historical offline handoff](HANDOFF.md): earlier walkthrough and build details.

Validation: 64 backend tests and 38 Android unit tests passed. Emulator checks covered connected login, uploads, scans, approvals and account isolation.
