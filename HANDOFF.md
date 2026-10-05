# Ditto Android handoff

The supplied Kotlin/Compose app and FastAPI backend were extended in place. The delivered Android APK is a **debug-signed, self-contained offline demo**, not a production release. It needs no build-machine backend, internet connection, Instagram account, API credentials, or physical phone. The supplied older `DITTO-release.apk` is a legacy artifact and is not the updated delivery.

## Install and access

Install `apk/DITTO-offline-demo-debug.apk` on Android 8 or later. Open Ditto, complete the three onboarding screens, and create a device-local account with an email-shaped identifier and a password of at least ten characters. No email is sent. Device-local credentials and server credentials are separate. Logout is in the top bar. Sessions expire after seven days; a password reset service is unavailable.

The emulator account used for verification is `creator@example.test` / `secure-demo-123`. This account is local to the test emulator and is **not preinstalled in the APK**. On another installation, create your own account.

## Demo walkthrough

1. Home displays protected originals, open cases, pending approvals and resolved cases. Tap **Scan for matches** or **Originals**, choose **Sunset Travel Reel**, and run the scan. Frames are actually decoded and hashed; the job and its completion are persisted. Existing candidates are deduplicated.
2. Cases → Pending → `@travel_reuploads`. Review both generated videos, measured similarities, publication metadata, rule confidence, and the proposed attribution request.
3. **Approve action** shows the exact recipient, sandbox channel and message. Approve the sandbox action. This records a sandbox receipt; nothing reaches Instagram.
4. Tap **+7 days**. Due cases receive a simulated no-response observation, producing an escalation proposal. It requires a fresh approval.
5. Approve again, then **Simulate weekly follow-up** → **Attribution added**. The case resolves and its timeline persists across process restarts.
6. `@portraitlighting` is an unrelated example: no automatic enforcement. `@credited.demo` and `@authorized.demo` match the video but close without outreach because attribution or permission is recorded separately in the synthetic registry.
7. `@glowup.skincare` is an explicitly simulated fake-endorsement/altered-script scenario. It has authored transcript examples and abstract video assets, not an actual person's likeness or speech. It produces a **Human Review Request**. No validated deepfake detector, face encoder or ASR engine runs.
8. Profile → Reset demo data rebuilds the current account's seeded cases. Uploaded originals remain. Filters, draft editing, rejection and deferral are available. Deferral leaves the action awaiting approval.

## Android build

Requires JDK 21 and Android SDK 35. From `android`, set `JAVA_HOME` and `ANDROID_HOME` for your machine and put `sdk.dir=<SDK path with forward slashes>` in `local.properties`.

```powershell
.\gradlew.bat assembleDebug testDebugUnitTest --console=plain
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`. Package: `com.ditto.app.debug`; version: `1.1.0-demo-debug`. Copy it to the delivery filename if rebuilding. Signing keys must remain outside source control. `assembleRelease` in the supplied project also uses a debug signing key; it does not produce a production-signed release.

The workspace's downloaded tooling is in the parent `tooling` directory: `java`, `android-sdk`, `gradle-home`, `venv`, and `avd`. Those are local tools, not app source. The Android SDK was installed and a hardware-accelerated API 35 x86_64 emulator used. `10.0.2.2:8010` remains the development backend build property; **the delivered app uses the on-device repository and does not depend on that URL**.

## Backend setup, migration and seed

Python 3.12 was used. From `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Use `/docs` to call `POST /api/auth/signup`, then authenticate with `Authorization: Bearer <token>`. Call `POST /api/demo/seed` to seed **that user**. Login, `/api/auth/me`, and logout are implemented. Tokens are opaque, expiring and stored as digests on the server. Passwords use PBKDF2-HMAC-SHA256 with independent random salts. Authenticated ownership checks cover media, cases, scans, mutations, stats and activity. Uploaded media is private and returned only by an authorized media endpoint. Legacy unowned records in the supplied database are preserved and hidden from authenticated users.

SQLite is the verified default. PostgreSQL uses `DITTO_DATABASE_URL=postgresql+psycopg://...`; its driver and migrations are included, but no PostgreSQL instance was available for execution testing. Apply migrations before starting a deployed server. Only expose a server through an appropriately configured HTTPS deployment.

The backend additionally records creator profiles, fingerprints, scan jobs/stages, evidence, structured deterministic agent decisions, approval snapshots, dispatch receipts and in-app notification records in normalized tables. Per-case deadlines and follow-up events form the persisted scheduler queue. `/api/content/{id}/scans` and `/api/notifications` are authenticated; notification read updates enforce ownership. These server notification records do not provide push delivery or synchronize into the offline Android repository.

The Docker build context is the project root so generated videos are included. `docker compose up --build` is supplied as a deployment option but was not run here because no Docker daemon was used. `DITTO_MEDIA_ROOT` must point to persistent private storage; Compose maps it under `/data/media`.

In a second backend terminal, run the durable sandbox scheduler:

```powershell
.\.venv\Scripts\python.exe scripts/scheduler.py
```

Run **one** scheduler process. It polls persisted deadlines every 30 seconds; failed checks are retried on a later tick. `POST /api/demo/advance-clock?days=7` advances that user's persisted demo clock and checks due cases. Approval remains required for escalation dispatch. Server dispatch attempts have unique receipt keys; mobile mutations are serialized and committed transactionally. Android uses WorkManager to check persisted due dates approximately every 15 minutes, subject to OS scheduling.

## Dataset and evaluation

```powershell
# From backend
python scripts/generate_dataset.py
python scripts/evaluate.py
python -m pytest tests -q
```

The generator uses deterministic procedural scenes and a fixed declared seed. It writes 15 originals and 165 labelled derivative pairs covering exact, crop, resize, watermark, caption, re-encoding, credited, authorized, ambiguous, unrelated and simulated fake-endorsement examples. Five creators supply demo assets; ten separate creators supply held-out evaluation. No classifier was trained and the 0.80 detection threshold was prespecified. There are no fabricated human-reviewer results.

`demo_data/evaluation.json` reports 110 held-out pairs: TP=90, FP=0, TN=20, FN=0, precision=1.0, recall=1.0, F1=1.0, false-positive rate=0.0. **These metrics describe only the easy generated near-duplicate task.** They do not establish real-world performance, permission, infringement, policy calibration or deepfake-detection accuracy. Five aligned frames can miss cuts, timing changes or adversarial edits. The confidence presented in the app is an **uncalibrated deterministic rule score**.

Android bundles the demo MP4s in `app/src/main/assets/corpus`. Regeneration of the dataset alone does not automatically update the packaged assets; copy the five demo creators' generated MP4s into that directory and rebuild if intentionally changing the corpus.

## Verification and practical limits

Automated backend tests cover authentication, isolation, session revocation, genuine media decoding, invalid media rejection, scan execution, approvals, duplicate approval prevention, renewed escalation approval, credited/authorized reuse, synthetic review, and resolution. Android unit tests cover the state machine and deterministic policies. Emulator screenshots and XML captures are in `output/screenshots`.

Validation completed: 38 Android unit tests and 62 backend tests passed. Separate backend processes verified persisted sessions, dispatch state and follow-up deadlines. Emulator account switching was checked in the same process: six originals in the creator account, five in a second account, with the creator's private upload absent from the second account. Early screenshot captures document development states; captures numbered 12 onward show the corrected account scoping and current labelled scenarios.

Live Instagram discovery, Meta account connection, external outreach/report filing, LLM reasoning, transcript extraction, facial embeddings and validated manipulation detection are **unavailable**. Credentials alone do not enable them. No content removal or guaranteed takedown is claimed. Notification preferences are stored, but push delivery is unavailable. Captions and other source data never execute instructions; the deterministic adapters do not invoke an LLM.

This implementation preserves the existing native Android architecture. An iOS client and shared cross-platform UI were not built or tested. The backend API and generated dataset can be reused by a future client. Production signing, live provider adapters, server synchronization in the Android client, independent policy calibration, a real-world detection benchmark, PostgreSQL deployment verification, and notification delivery remain deployment/product work.
# Latest visual update — 1.2.0 sunset demo

The newest APK is `apk/DITTO-sunset-demo-debug.apk`. It replaces the visual
identity with off-white and charcoal, pink/peach/coral/sunrise-yellow accents,
bundled Space Grotesk/DM Sans/Caveat fonts, a quotation-shaped d logo, animated
sunrise decoration, and interactive dashboard approval cards. It remains an
offline, debug-signed demo. This build was compiled, installed, and visually
checked on the existing API 35 emulator. Previous validation below refers to
the underlying feature implementation, which is preserved.

Current screenshots: `output/screenshots/21-sunset-home.png` and
`output/screenshots/22-sunset-cases.png`.

SQLite is selected for the first hosted backend. No Supabase integration is
used. Hosting activation and provider credentials are still outstanding; see
`docs/PRODUCTION-NEXT.md` for the next steps. Android backend synchronization
remains to be implemented before a connected production release.

# Connected test update — 1.3.0

Newest APK: `apk/DITTO-connected-test-debug.apk`. On the sign-in page choose
Connected test and paste the Codespaces backend root URL. See
`docs/CODESPACES.md` for launch, port visibility, private data and backup details.
The server is now selectable at runtime; local accounts and server accounts are
separate. The app does not silently fall back to local data after a connection
failure. Scans and approved mutations use server API records. The pink design is
preserved. Provider adapters remain sandboxed; this is not a production release.

