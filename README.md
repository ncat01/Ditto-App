# Ditto - An Agentic AI Content Credit System

Version **1.6.0-integration** adds a connected Android sandbox to the existing Kotlin Compose app and FastAPI backend, with a pink sunrise/sunset interface, bundled fonts and a new quotation-shaped logo.

Install `apk/DITTO-1.6.0-integration-debug.apk` (Android 8+; debug signed). Choose **Cloud account** at sign-in and enter your backend HTTPS URL, or use **Offline demo** for device-local accounts. Connected mode supports server accounts, SQLite storage, private video uploads/playback, scans, approvals and follow-ups. Accounts in the two modes are separate.

Start with [Codespaces setup](docs/CODESPACES.md). The repository includes automatic backend setup in `.devcontainer/`. SQLite requires no database API key. Codespaces is a development environment with idle shutdown and usage quotas; this delivery is a connected test rather than an always-on production deployment.

Discovery uses generated demo assets and outreach is sandboxed. Live Meta discovery/messaging, face embeddings and ASR are not connected. No provider credentials, account databases or private uploads are included in source.

Version 1.4.0 adds account-bound Instagram video import and Gemini draft previews in Android. Follow [integration setup](docs/INSTAGRAM.md). Provider access has been checked in Codespaces; the new app flows still require the updated backend and operator account binding.

- `android/`: Kotlin, Compose, Room and encrypted server sessions.
- `backend/`: FastAPI, SQLAlchemy, Alembic and account-scoped authenticated APIs.
- `demo_data/`: generated video manifest and matcher evaluation.
- [Next production steps](docs/PRODUCTION-NEXT.md).
- [Historical offline handoff](HANDOFF.md): earlier walkthrough and build details.

Validation: 105 backend tests and 38 Android unit tests passed; fresh migrations reached 008_remote_media with SQLite integrity confirmed. New Appwrite route tests use provider mocks. The user separately verified live private storage upload/deletion. New deployment and signed release have not been verified on infrastructure/devices.

Version 1.5.0 adds a five-step illustrated guide immediately after an account first signs in, including sign-up. Completion is stored per account and backend; Profile ? How to use Ditto reopens it. It covers account connection limits, importing originals, evidence review, Gemini draft review and sandbox approval.

Current implementation: account recovery/verification/deletion, actual app screenshot guide, consented web-image search and measured candidate comparison, optional private Appwrite storage with owner-checked playback and durable cleanup. See [deployment preparation](docs/DEPLOYMENT.md). SQLite remains the active metadata store; Appwrite Functions/metadata migration and commercial deployment are unfinished. No production-ready claim is made.
