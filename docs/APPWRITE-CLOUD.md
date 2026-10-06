# Appwrite deployment candidate

The existing Android/FastAPI integration continues to run. `backend/cloud` is an isolated, incomplete Appwrite backend candidate; do not change the production Android origin to it yet.

Implemented in the candidate: private Appwrite accounts and hashed sessions, password-reset/session revocation, email-verification queues, account closure with retryable file cleanup, request budgets, resumable 5,000,000-byte chunks up to 20,000,000 bytes, integrity checks, measured image/video fingerprints and owner-scoped asynchronous comparison results. SMTP acceptance is not recipient delivery. Interrupted email jobs become unknown and are never resent automatically.

The API and worker have separate entrypoints: `cloud/main_api.py` and `cloud/main_worker.py`. The adapter uses Appwrite's Python `body_binary` and `query_string` properties and keeps the platform-injected key outside ordinary request headers. Only the API Function may be publicly executable. Worker execution must remain private; configure a periodic schedule and asynchronous wakes after its live runtime has been validated.

## Reviewable artifacts

From the repository root:

```bash
.venv/bin/python backend/scripts/setup_appwrite_cloud.py
.venv/bin/python backend/scripts/package_appwrite_cloud.py
.venv/bin/python backend/scripts/plan_cloud_migration.py --sqlite .ditto-data/ditto.db
```

These commands make no cloud changes. Schema output contains three new v2 tables, separate from the manually created Originals table. The migration inventory prints counts, never account records, tokens or password hashes. Packaging uses an explicit source allowlist and excludes SQLite code, databases, media and secrets.

`setup_appwrite_cloud.py --apply` requires a private temporary `APPWRITE_SETUP_KEY` with schema access. It creates missing v2 tables and validates existing ones; it never repairs differences by deleting or overwriting a table/column. Columns and indexes must finish building before use. Live schema compatibility, transactions and permissions still need checks against this project's Appwrite version.

## Before deployment or cutover

The candidate does **not** yet implement the existing Instagram OAuth/import, case review/dashboard, Google discovery and live outreach workflows. Android does not yet speak its resumable upload/job protocol. Existing SQLite data has not been migrated. Function creation, runtime build, schedule, HTTPS origin, quota monitoring and restoration have not been performed.

Keep the current backend and its private data. Finish the missing routes/client changes, migrate a consistent backup into new tables, verify two-account isolation and media integrity, then perform a controlled cutover. Function deployment requires authenticated management access that this local session currently lacks; Codespaces secrets are not automatically shared with this session.

Public operator: **Svarsha T**. Support: **svarsha.t@gmail.com**. Backup retention and the final privacy/deletion wording still require an explicit operating policy.

Runtime references: [Appwrite execution limits](https://appwrite.io/docs/products/functions/execute), [Python runtime types](https://github.com/open-runtimes/open-runtimes/blob/main/runtimes/python/versions/latest/src/function_types.py), [TablesDB transactions](https://appwrite.io/docs/products/databases/tablesdb/transactions).
