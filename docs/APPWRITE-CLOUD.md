# Appwrite deployment architecture

`backend/cloud` uses private native Appwrite TablesDB rows and Storage files without SQLAlchemy or local SQLite. The existing development backend is preserved.

`ditto-api` serves authenticated Android routes and public policy/account pages. `ditto-worker` processes durable owner-scoped upload, comparison, Instagram, search, draft, cleanup and explicitly approved email jobs. Both stay disabled/private during staging. Runtime credentials are dynamic server keys; management credentials never enter the Functions or APK.

Accounts, encrypted records and budgets use new versioned tables. Existing Originals tables are retained. Revocable sessions, native transactions, per-owner checks and private file permissions protect access. Native concurrency and binary transport also require live staging checks; mocks cannot establish those properties.

Uploads use 5 MB chunks, a 20 MB total limit, checksums and persisted reconciliation receipts. Slow hashing/provider work is asynchronous. Images and sampled video frames produce measured perceptual hashes. Cases leave ownership and permission judgments to a human. Web-image results are unverified leads; no platform-wide Instagram discovery is claimed.

Migration preserves login hashes and encryption keys, archives historical rows privately and transfers measured originals. Historical demo cases are not activated as real evidence. Missing media or ambiguous ownership require review. Source databases/files are never deleted.

Backup exports are independently encrypted, authenticated and sequenced. Restore requires empty private targets, invalidates sessions and leaves uncertain outbound messages unknown. A live restore drill is still required.

See [COMMERCIAL-DEPLOYMENT.md](COMMERCIAL-DEPLOYMENT.md) for the consolidated batch, scopes and launch checks.
