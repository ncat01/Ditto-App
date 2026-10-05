# Ditto — An Agentic AI Content Credit System

The existing native Android app and FastAPI service have been extended with a warm creator interface, device-local and server authentication, isolated account storage, real five-frame video hashing, generated video evidence, persistent scan jobs, human-approved sandbox actions, and durable follow-ups.

**Start here: [HANDOFF.md](HANDOFF.md)** for installation, demo access, walkthrough, backend migrations and seeds, dataset generation, evaluation, build commands, and deployment limits.

- Updated APK: `apk/DITTO-offline-demo-debug.apk` — debug-signed Android 8+ offline demo, version `1.1.0-demo-debug`.
- Android source: `android/` (Kotlin, Compose, Room, DataStore, WorkManager).
- Backend source: `backend/` (FastAPI, SQLAlchemy, Alembic, opaque expiring sessions).
- Dataset: `demo_data/manifest.json`; measured held-out results: `demo_data/evaluation.json`.
- Emulator captures and verification evidence: `output/`.

Live Instagram discovery, external messages/reports, LLM calls, face embeddings, ASR and validated manipulation detection are unavailable. All outreach is sandboxed; simulated scenarios and uncalibrated rule scores are labelled. The Android client runs locally and does not synchronize with the separately authenticated backend. No iOS build was produced.

The earlier README is preserved in `docs/LEGACY_README.md` as historical documentation; its implementation and integration claims are superseded by this handoff.
# Connected Codespaces test — version 1.3.0

Codespaces configuration is included in `.devcontainer/devcontainer.json`.
Start the backend with `.venv/bin/python backend/scripts/codespaces.py start`.
The Android client now supports **Connected test** at sign-in with a runtime
backend URL, server accounts, account-isolated API data, real uploads, server
scans and approvals, private server video playback, and visible connection errors.
The pink sunrise/sunset design and offline device accounts are preserved.

Read [Codespaces launch and phone setup](docs/CODESPACES.md). SQLite needs no API
key. This is a connected sandbox test: discovery is synthetic, outreach is
recorded locally on the server, and live providers are still unavailable.
Codespaces is a metered development environment with idle shutdown, not continuous
production hosting. No provider credentials or private account data are committed.

