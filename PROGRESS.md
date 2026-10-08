# Commercial release progress

## Current status — 1.8.9 (2026-10-08)

The signed APK/AAB are built for `com.ditto.app`, version 1.8.9/code 18, Android 8+ and target API 36. The latest Railway deployment succeeded and reports 1.8.9. Live health returns HTTP 200 and a connected database. **The real copied-Reel acceptance test failed. Public commercial launch is not certified; [BLOCKERS.md](BLOCKERS.md) is authoritative.**

- Validation: **129 backend tests and 33 Android unit tests pass**. Signed APK/AAB artifacts and the workstation `releases/Ditto-1.8.9.zip` are prepared.
- Originals now lead to a prominent **Find copies** action. Selecting a saved original scrolls to its search controls; a successful Instagram import selects the returned original. Saving or importing an original alone does not silently start a provider search.
- Search consent submits a durable job and presents actual queued/running/completed/failed states. Returning Home does not stop a submitted search; reopening the original restores its receipt and results.
- The client retains an ambiguous submission's request ID and recovers that exact server receipt. Explicit retry reuses the ID. Confirmed client rejection clears pending state and preserves direct comparison; network failure, HTTP 408 and server failure retain recovery.
- A malformed or failed receipt is never presented as a completed zero-match search. Successful empty results explain the limit of indexed coverage. Search activity records cover queued/completed/failed/interrupted work.
- Network validation recovery reconnects the repository, and closed repositories cannot publish stale snapshots after logout. Customer messages hide raw connection details and internal fingerprint labels.
- Earlier completed web searches saved before durable job receipts restore from the legacy records without another provider query or quota reservation. Live restoration returned 50 source URLs, including two Instagram links and zero exact matches; the known copy was absent. Direct comparison records are not shown as web searches.
- Railway deployment `72919b8b-f368-4114-85e8-852fe5ece561` succeeded from source `813710c`. The live database connection and restored search endpoint were checked after deployment.
- Profile verification controls follow the host's truthful email capability. The owner declined sender credentials; recovery/verification email and SMTP remain unavailable. Reviewed outreach opens the user's email app.

### Real Reel acceptance evidence

The original `DeIBHC7NOcX` was imported through the authorized Instagram integration. Its two earlier completed searches each saved 50 source URLs. Neither includes the known suspected-copy Reel `DeLwnWiz9lW`. Restoration preserves those actual results and does not substitute a fabricated match.

**Current real copied-Reel acceptance check: failed.** One fresh normal owner search completed with 50 source URLs, including six Instagram links and zero exact matches. Neither the original `DeIBHC7NOcX` nor the specified copy `DeLwnWiz9lW` was returned. The job completed successfully, but it failed the required known-copy discovery check. No copied-Reel discovery success is claimed. SerpApi searches indexed public pages and cannot promise all public Instagram Reels.

That video search used ten provider query units. The live owner allowance is 20 units/month, with all 20 now used; the global cap remains 225 units/month. Restoring saved results does not consume additional units. Temporary generated UI-verification account/media were removed, and emulator app data was cleared.

Non-role professional Instagram users still require Meta review, Advanced Access and publishing. Trial hosting continuity, email capability, the remaining infrastructure requirements and store approval are not completed by signing the APK.

Deliverables: [APK](apk/DITTO-1.8.9-release.apk), [AAB](apk/DITTO-1.8.9-release.aab), and workstation `releases/Ditto-1.8.9.zip`. No physical phone is connected for current handset acceptance.

## Historical implementation record

The entries below record earlier states and test totals. They are retained for traceability; the current status above and BLOCKERS.md supersede their launch-status statements.

## P1 ? Repository audit completed (2026-10-06)

Preserve the existing Kotlin Compose Android app and FastAPI/SQLAlchemy backend.
Permanent Android package: `com.ditto.app` (confirmed by owner).
Target host: Railway (owner has a free account; no paid usage authorized).

Baseline acceptance command:
`tooling/venv/Scripts/python.exe -m pytest "Ditto Phoneapp/backend/tests" -q`
Result: **138 passed, 1 warning in 10.95s**.
Evidence: [backend baseline](docs/evidence/p1-backend-baseline.txt).
Android compilation/unit tests before the latest tutorial edits: BUILD SUCCESSFUL;
this is baseline evidence, not final release certification.
ADB: physical Vivo `10BE830S1B0010T`, model V2347, status device; emulator also attached.

### Audit findings
- Existing SQLAlchemy models, Alembic migrations, API authorization, OAuth, private uploads,
  real pHash comparisons and provider adapters can be retained and strengthened.
- Current production Compose still uses SQLite and local/Appwrite storage. It does not
  implement the requested PostgreSQL + Redis + object-storage + durable worker stack.
- Android runtime includes local mock agents, demo clock and synthetic corpus assets.
  Removing visible toggles is insufficient: remove runtime imports and packaged assets.
- Existing auth uses PBKDF2 and opaque sessions, not the requested Argon2/rotating-refresh design.
- Existing Appwrite private API and worker built, but live signup verification failed.
  This deployment does not satisfy the new PostgreSQL requirement; no public launch occurred.
- Docker CLI is unavailable in this local session. Container restart persistence is untested.
- No live SMTP sender/inbox, Meta public-user review or Railway deployment access verified.

### Architecture plan
P2: strengthen existing SQL backend, PostgreSQL migrations, Argon2/rotating auth,
S3 private storage and cross-user tests. Preserve existing stored user data.
P3?P6: real ffmpeg fingerprints, explicit unavailable face/manipulation evidence,
discovery and structured LLM adapters, persisted queue and exact-action approval/dispatch.
P7: API-only Compose app, no synthetic runtime/assets, Aura tokens and accessibility.
P8: build release APK/AAB with private signing; inspect physical-device captures.
P9: Railway API/worker/scheduler/Postgres/Redis/object-storage config, CI and launch evidence.

No phase beyond P1 is certified complete. No commercial release is installed.

### Local implementation verified (2026-10-06)
- Permanent release package remains `com.ditto.app`, as requested by the owner.
- Android now uses server authentication; synthetic corpus assets and mock agents were
  preserved under `/eval/legacy_android`, removed from main runtime source/assets.
  Removed the offline login copy, generated evidence illustrations, demo clock controls,
  simulated follow-up picker and synthetic likeness results. Missing providers show unavailable.
- Approval sheet now opens the actual email recipient/message review component.
- Android assembleDebug and unit tests passed; this is a validation artifact, not an
  official release or proof of a hosted production backend.
- APK/source synthetic-content inspection passed. The Gradle preBuild guard and mobile
  refresh-token handling passed the subsequent Android build and unit tests.
- SQL authentication now hashes with Argon2, uses 15-minute access sessions and rotating
  refresh tokens, revokes token families on replay/logout/reset, and migrates old hashes
  after successful login. Account deletion verifies Argon2 correctly.
- Full backend suite: 141 passed, one dependency deprecation warning. Evidence:
  `docs/evidence/p2-auth-tests.txt`. Android evidence: `docs/evidence/android-runtime-cleanup.txt`.
- Mobile refresh tokens are stored in the Android Keystore vault; refresh is serialized
  before authenticated requests. Mutations are never automatically retried.
- Backend defaults to non-demo mode; missing OAuth/email credentials no longer block
  all API startup. Docker source no longer bundles demo videos and installs ffmpeg.
  Docker execution remains unverified because its runtime is unavailable.
- P2 remains incomplete: PostgreSQL container verification,
  durable worker/object storage and removal of legacy backend demo code are outstanding.
- Railway deployment is not performed: no project access or sufficient free capacity verified.

### Backend runtime cleanup and small deployment preparation (2026-10-06)
- Owner confirmed a maximum of 25 users, free Railway only, and no available credit.
  No upgrade, paid service or public deployment was initiated.
- Removed production mock agents, synthetic hash fallback, demo seed/clock endpoints,
  simulated case dispatch and simulated follow-up paths. Retired source/assets and
  five simulation-dependent test files (53 historical tests) are preserved under `/eval`.
- Production accounts start empty even when an old demo environment flag is present.
  Added guards covering missing-file fingerprints, empty signup data, removed routes
  and forbidden simulation imports. Account-deletion coverage now uses a real PNG upload.
- Current production suite: **91 passed**, one dependency deprecation warning.
  This replaces the earlier 141-test total because evaluation tests no longer belong
  to production validation. Log: `docs/evidence/backend-runtime-cleanup.txt`.
- Prepared PostgreSQL local Compose with persistent database/media volumes, DB health
  checks and loopback-only API exposure. Prepared Railway Docker build/health config,
  platform PORT support and DATABASE_URL-to-psycopg normalization shared by migrations.
- These deployment configurations have not run: Docker and Railway access are unavailable.
  Durable SQL jobs, S3 integration, real case workflow/delivery and PostgreSQL restart
  verification remain unfinished. Existing measured comparison and own-media upload
  services remain; removed simulation services are not substituted with fake results.
- The existing physical-phone installation is still the previous debug build.
  No final commercial APK/AAB has been generated or installed.

### Live Railway verification (2026-10-06)
- Owner clarified that a 30-day/$5 Railway trial remains and authorized using it.
  Authenticated the official Railway CLI and created project
  `d6b6fd1c-5569-4ff6-a3a3-fd0559b851be` with PostgreSQL and `ditto-api`.
- Live HTTPS origin: `https://ditto-api-production-7e7f.up.railway.app`.
  Existing Instagram/token-encryption secrets were transferred directly from encrypted
  local configuration into hosted variables, never printed or bundled into source/APK.
- Persistent private media volume attached at `/data`. Startup initializes its private
  directory then drops privileges before migrations/API execution.
- Verified HTTPS DB health, empty signup, actual PNG upload/playback, cross-user denial,
  measured image comparison and refresh rotation. All temporary accounts/media removed.
  Evidence: `docs/evidence/railway-live-api.txt`.
- Verified PostgreSQL account/session and exact private image bytes survive an API
  restart; temporary persistence data removed. Evidence:
  `docs/evidence/railway-restart-verification.txt`.
- Release APK/AAB build is in progress with existing owner identity and the hosted origin.
  This establishes core hosted functionality, not completion of the remaining durable
  jobs, live case-action delivery, public Meta review or final commercial acceptance.

### Signed hosted Android installation (2026-10-06)
- APK/AAB release build passed (3m33s), package `com.ditto.app`, version 1.8.0/code 9.
- APK verified with v2 signature; certificate matches the retained owner key
  (SHA-256 `35ed1452a009c567a5d5308093b6a9e8ae9f7555ecbd427f535703c2201cf506`).
  AAB JAR signature verified. No debuggable flag in APK badging.
- Production APK synthetic-source/assets guard passed. Its API origin is the verified
  Railway HTTPS host; users do not enter backend addresses or provider keys.
- Installed and launched successfully on physical Vivo `10BE830S1B0010T`.
  No release-package entry in recent crash buffer. Visual acceptance remains pending:
  phone was locked; initial capture was black and does not establish a successful UI check.
- Owner requested to unlock/open Ditto and save the new Meta callback. Neither action
  has been confirmed yet. Remaining commercial workflow blockers still apply.
- Deliverables: `apk/DITTO-1.8.0-release.apk`, `apk/DITTO-1.8.0-release.aab`.

### Hosted processing and simplified outreach (2026-10-06)
- Migration 010 and PostgreSQL-backed comparison jobs deployed. Case, measured evidence and completion commit atomically; row locks permit deterministic retry after rollback.
- Live queued comparison, real owned review case and private candidate playback verified; temporary accounts/media removed. Backend tests: 94 passed.
- Optional exact SMTP approval uses idempotent receipts and commits unknown before attempting transport; uncertain attempts never automatically retry. Mocked acceptance/failure tests pass. SMTP remains disabled; no real delivery claimed.
- Owner declined Gmail credentials. Android opens reviewed drafts in the phone email app; recovery/verification sender remains unavailable.
- Signed 1.8.1 installed; 1.8.2 adds simplified email and removes obsolete corpus/progress views.
- Owner reports Meta insufficient developer role. Account invitation/public Meta approval remain external requirements.
- Accidental separate railway-stage project was inspected (zero volumes/database) and removed; production intact.
- BLOCKERS.md is the current authoritative status; earlier entries record historical states.


## 2026-10-06: SerpApi selected
Reverse search now uses private multipart image uploads to SerpApi Google Lens instead of Google Cloud Vision. Images are compressed below the provider upload limit; video uses five frames. Consent and privacy copy name SerpApi and Google Lens. Backend caps: 225 attempted units/month globally, 10/account/month, 45/hour globally. All 95 backend tests pass. Private key setup script and docs/SERPAPI-SETUP.md prepared. No SerpApi key received, no live provider search verified, and this change is not yet deployed or installed on the phone.

SerpApi backend deployed successfully (bbcaa3c2-59f2-478d-961b-baf9783dbde7). Live test stopped with HTTP 503; direct provider diagnosis returned HTTP 401 / invalid API key. Generated accounts and media were removed. Key replacement requested privately. Signed 1.8.4 rebuild underway after Gradle cache access failure; no new phone install claimed.

Signed Ditto 1.8.4 APK/AAB built successfully; APK certificate matches existing owner key and installed on Vivo 10BE830S1B0010T preserving data. Hosted core verification passed (signup, private media, durable comparison, isolation, rotating tokens and temporary-account cleanup). Phone was locked, so no visual UI verification claimed. Live reverse search remains blocked by SerpApi invalid-key response until privately saved replacement is provided.

SerpApi activation completed: clipboard key privately saved and provider account accepted (HTTP 200; 250 searches before test). Railway deployment 427c8a66-f32a-4f6a-a1ae-e259eddc4393 succeeded. Hosted live generated-image upload/search returned 50 unverified leads; explicit consent and cross-user isolation verified. Core durable comparison and token-rotation checks passed. Temporary accounts and generated media removed. This verifies reverse image search, not comprehensive Instagram coverage or video-match accuracy.

### Visual release 1.8.5 (2026-10-07)
- Replaced the beige visual system with a violet, pink, aqua and gold identity, a new
  Ditto echo mark, updated launcher art, Space Grotesk/DM Sans/Caveat typography,
  translucent cards and a floating rounded navigation bar.
- Added a live ambient aura to the entire app. Each press emits a seven-point colored
  split without consuming the gesture, so scrolling and controls continue to work.
- Rebuilt onboarding, sign-in, post-signup tutorial, home and profile. New accounts and
  home data begin empty; no synthetic creators, reels, cases or approvals are shown.
  The primary home action is reverse search/comparison. Logout remains in Profile.
- Instagram connection status polls the hosted API every five seconds while disconnected
  and when the app resumes, then presents the connected account without a refresh button.
- Emulator visual review completed for onboarding, aura response, login, real signup,
  tutorial, empty home and profile. The temporary live account was deleted afterward.
  Evidence: `docs/evidence/ui-1.8.5-*.png`.
- `assembleDebug`, Android unit tests, release lint, R8, signed APK and signed AAB passed.
  Package `com.ditto.app`, version `1.8.5`/code `14`; APK signature matches the retained
  owner certificate (`35ed1452a009c567a5d5308093b6a9e8ae9f7555ecbd427f535703c2201cf506`).
  The signed release installed and launched on the Android emulator.
- Deliverables: `apk/DITTO-1.8.5-release.apk` and `apk/DITTO-1.8.5-release.aab`.
- Signed 1.8.5 installed successfully on the connected Realme CPH2585 (`be6829d5`);
  Android reports version code 14/name 1.8.5 and the application process starts. The
  handset was locked during capture, so final owner visual acceptance remains pending.
  Meta public-user approval, an email sender, and store review remain external launch
  requirements; this build does not claim those approvals.

### Downloadable signed release 1.8.8 (2026-10-08)
- Exact and visual Lens queries now run explicitly for images and five sampled video
  frames. Successful empty responses no longer abort the remaining queries. Search
  jobs persist progress/results, protect repeated submissions and restore results on
  returning to the original. Live generated-image search returned unverified leads;
  this does not establish exhaustive public Instagram or copied-Reel coverage.
- Comparison screens include Home navigation. Case cards, detail percentages and
  filters use measured content similarity. Customer-facing rule-score labels and the
  synthetic likeness category choice were removed. Images display as private image
  evidence; videos retain playback. Home/Cases use actual downloaded original previews.
- Backend deployment `cca7b51a-d7ff-41c5-ba3b-054b29cbddda` succeeded on the existing
  Railway trial service, commit `50e227be91a1363c533f5a716a76c38556042850`. Live case
  list/detail identify image evidence correctly, and protected original/candidate PNG
  bytes match. All 120 backend tests pass, including actual image/video media checks.
- Android 18 unit tests, release lint, R8, APK and AAB builds pass. Package
  `com.ditto.app`, version 1.8.8/code 17, target API 36. APK v2 signing matches the
  retained owner certificate; AAB signature and APK 16 KB ZIP alignment verified.
- Final signed APK installed and launched on the Android emulator (cold launch 780 ms).
  Visual checks show actual paired images, 100% content similarity and working Home
  return. An earlier emulator GPU shader stall required a restart; the final build
  remained responsive. No physical phone is connected; handset acceptance is pending.
- Generated UI verification account, its content/case and private credential fixture
  were removed. The emulator's test session was cleared.
- Deliverables: `apk/DITTO-1.8.8-release.apk`, `apk/DITTO-1.8.8-release.aab` and the
  workstation `releases/Ditto-1.8.8.zip` with installation instructions/checksums.
  APK SHA-256: `65b85ebb54edaf23ed640d2937e71341def95b8758754cea16170a1f47e3755f`.
  AAB SHA-256: `d059146f495a7841702cfa03999e989e51f079c0b9cd66c0113d82d8fc71d740`.
- Customers can sign up, upload, search and compare without Instagram or tester roles.
  Connecting non-role professional Instagram accounts still requires Meta Advanced
  Access approval and publishing. Operator steps are in `docs/INSTAGRAM_SIGN_IN.md`.
  The signed downloads do not certify public launch; `BLOCKERS.md` remains authoritative.
