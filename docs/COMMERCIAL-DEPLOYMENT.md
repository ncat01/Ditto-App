# Consolidated deployment

Owner: **Svarsha T**. Support: **svarsha.t@gmail.com**. The implementation is prepared for private staging; public deployment and commercial readiness remain unverified.

## One staging batch

In the existing Codespace:

```bash
git pull --ff-only
.venv/bin/python backend/scripts/commercial_batch.py --stage
```

This installs pinned dependencies, checks compatibility, runs backend tests, packages allowlisted code, creates isolated schema and disabled private Functions, and probes live transactions, session isolation and private image storage. Generated probe accounts/image are cleaned up. It does not publish, migrate data, send messages or purchase a plan. A private report is saved to `.ditto-data/cloud-deployment.json`.

Supply a temporary **APPWRITE_DEPLOY_KEY** privately to that runner. The existing storage-only key cannot deploy. Never paste credentials or private database contents in chat.

Management scopes:

```text
databases.read tables.read tables.write columns.read columns.write
indexes.read indexes.write rows.read rows.write buckets.read
files.read files.write functions.read functions.write
executions.read executions.write rules.read
```

Runtime dynamic scopes:

```text
databases.read tables.read rows.read rows.write
files.read files.write executions.write
```

Reuse `INSTAGRAM_APP_SECRET` and the existing private `.ditto-data/token-encryption.key`. Do not replace an encryption key used by stored tokens. Optional provider settings: `SMTP_HOST`, `SMTP_PORT` (465 or 587), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `GOOGLE_CLOUD_API_KEY`, `GEMINI_API_KEY`, `VISION_MONTHLY_UNIT_LIMIT`. The runner copies only allowlisted configuration, never management keys or the legacy shared Meta token.

Without a stable `PUBLIC_BASE_URL`, staging attempts to discover the API's generated Appwrite HTTPS domain and rebuilds with that origin. A Codespaces origin is discarded. If no generated domain is returned, inspect the Function domain before supplying a stable HTTPS root. Register that origin plus `/api/integrations/instagram/callback` in Meta. Deployment does not provide Meta approval.

Without `--stage` the batch validates/packages locally and prints a credential-presence-only plan. Repeat live checks without rebuilding:

```bash
.venv/bin/python backend/scripts/deploy_appwrite_cloud.py --verify
```

## Migration and backup

First obtain an encrypted source backup, stop the owned development supervisor and confirm no writer is using SQLite/uploads. Read-only inventory:

```bash
.venv/bin/python backend/scripts/migrate_appwrite_cloud.py --sqlite .ditto-data/ditto.db
```

Review missing media/ownership, then use the actual existing upload root:

```bash
.venv/bin/python backend/scripts/migrate_appwrite_cloud.py --sqlite .ditto-data/ditto.db --media-root YOUR_EXISTING_UPLOAD_ROOT --source-frozen --apply
```

`--source-frozen` is an operator assertion, not a stop command. Migration retains source data, preserves password hashes/tokens, archives history and transfers measured originals with resumable receipts. It does not turn demo cases into evidence or change Android endpoints. Missing media or ambiguous ownership blocks cutover approval.

Run `backup_appwrite_cloud.py --help` for encrypted backup, inspection and restore. Set a separately backed-up private `DITTO_BACKUP_KEY`. Functions must be private/stopped with no in-flight executions. Restore only into empty targets; sessions are revoked and uncertain outbound jobs are not automatically resent. Complete a live restore rehearsal. Backup scheduling and owner-approved retention remain required; owner backups are never automatically deleted by these scripts.

## Android release

An owner-held signing key was created privately on the local workstation under `.ditto-data/release-signing/`. It is excluded from source bundles. Back it up separately and transfer privately if building elsewhere. `prepare_release_signing.py --create` never replaces an existing key.

Set `DITTO_SIGNING_STORE_FILE`, `DITTO_SIGNING_STORE_PASSWORD`, `DITTO_SIGNING_KEY_ALIAS`, `DITTO_SIGNING_KEY_PASSWORD` privately, then:

```bash
cd android
./gradlew assembleRelease bundleRelease -PdittoApiBaseUrl=https://YOUR_VERIFIED_API_ORIGIN/
```

Release requires a key and valid service origin. The debug APK is a validation artifact, not commercial distribution. Test signup, verification/recovery, Instagram return/import, playback, comparison, consent, email review and deletion on real devices.

## Publication

`launch_appwrite_cloud.py` prints required checks without writes. Owner evidence must match the archive checksum, staging report, exact HTTPS origin and Meta callback. Checks cover public Instagram authorization, actual inbox delivery, restore, migration, devices, key backup, policies, quotas and truthful discovery scope. Do not mark an unfinished check true.

```bash
.venv/bin/python backend/scripts/launch_appwrite_cloud.py --publish --evidence YOUR_PRIVATE_APPROVED_EVIDENCE.json
```

It enables the authenticated API and private worker with a five-minute fallback schedule, verifies public HTTPS/authentication and attempts rollback on failure. It makes no billing change or app-store submission. **Outreach remains disabled** until separate reviewed provider activation. Do not advertise dispatch while disabled. Hosting quotas may delay processing.

This local session cannot read secrets from another Codespace. Actual staging, Meta approval, SMTP tests and device evidence remain necessary before commercial launch.
