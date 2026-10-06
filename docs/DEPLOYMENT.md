# Prepared deployment, not launched

FastAPI + persistent SQLite remains the backend. Appwrite is optional private file storage, not a replacement for the SQLAlchemy metadata database. TablesDB metadata migration and Appwrite Functions deployment are unfinished.

## One controlled Codespaces update

After pulling the source, install backend/requirements.txt. Stop the supervisor before applying migrations, then restart with the storage setting:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python backend/scripts/codespaces.py stop
DITTO_MEDIA_STORAGE=appwrite .venv/bin/python backend/scripts/codespaces.py start
```

This is a development check. Existing local originals remain readable; new direct uploads use Appwrite and keep a local hashing copy. Maximum is 20,000,000 bytes. Formats are JPEG, PNG, WebP, MP4 and MOV. Existing Instagram-import ingestion still stores locally.

Verify with two fresh accounts: upload/play on A; B must receive 404 for A's media. Delete A and verify the remote file disappears after cleanup. APPWRITE_API_KEY stays on the server.

## Production infrastructure

Copy production.env.example to a private .env and fill the operator-owned credentials/domain. Run production_preflight.py for a redacted audit. Then validate docker-compose.production.yml with `docker compose --env-file .env -f docker-compose.production.yml config --quiet`. Deploy only after the release gates in PRODUCTION-NEXT.md are satisfied.

Caddy handles TLS; only its address is trusted for forwarded headers. Persistent /data holds SQLite and local hashing copies. The maintenance worker retries deletion jobs and never sends sandbox follow-ups. Docker/Caddy runtime has not been validated locally because Docker is unavailable. No production host has been provisioned.

## Backups and release

backup_bundle.py archives SQLite and referenced local originals with checksums. restore_bundle.py restores into a NEW directory, validates SQLite foreign keys and rewrites local paths. Keep backups encrypted and outside the live server. TOKEN_ENCRYPTION_KEY and the Android signing keystore need separate secure backups; normal source exports exclude them.

Appwrite remote files need a defined export/retention strategy before disaster recovery is promised. Deleting an account must not resurrect its old remote references through a backup restore. Define backup retention before publishing the final deletion policy.

Release builds require a stable production HTTPS origin and privately held DITTO_SIGNING_* settings; debug signing is not a release fallback. Appwrite Education is time-limited; plan for expiry. Real-device OAuth, email delivery, signed APK/AAB checks and Meta/store reviews remain release gates.
