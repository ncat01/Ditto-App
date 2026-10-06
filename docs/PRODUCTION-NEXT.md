# Commercial release readiness

Status: NOT READY for commercial launch. The current APK is a debug integration build.

## Implemented and checked

- Pink sunrise/sunset design and bundled licensed fonts.
- Authenticated server accounts, expiring sessions and private media access.
- Persistent SQLite database; no database API key is needed.
- Gemini drafting integration, previously verified against the provider.
- Per-user Instagram browser OAuth, encrypted token storage, refresh and disconnect. Backend configuration is verified in Codespaces; an actual OAuth login is still pending.
- Connect Instagram controls in the signup guide, Profile and Originals.
- Android release tasks require an explicit HTTPS endpoint and privately managed signing credentials. Debug signing is no longer a release fallback.

## Launch blockers

### Current implementation update (1.6.0)

Account recovery, verification, deletion, abuse limits, consented Google web-image search, measured candidate comparison and real tutorial screenshots are now implemented locally. Appwrite chunked storage, owner-checked playback and durable cleanup are implemented behind DITTO_MEDIA_STORAGE=appwrite. The user verified a private generated-image upload/deletion in Codespaces. These changes require the updated source; they are not a commercial deployment.

Appwrite TablesDB Originals is provisioned but is **not the active metadata store**. Accounts, sessions, cases and evidence still use SQLite. Appwrite Functions/metadata migration is unfinished. Existing Instagram-import ingestion still stores its media locally. A durable always-on backend is still needed for this architecture; Codespaces is development infrastructure.

Privacy/terms/deletion pages are factual drafts. SMTP credentials, actual operator identity, live recovery delivery, Meta public-user approval, Google billing-enabled discovery, live outreach implementation, release signing and real deployment/restore checks remain outstanding. No commercial-ready claim is justified. The numbered items below are the earlier audit; the update above records work completed since that audit.

1. Live OAuth login and import must be tested on a device. Meta approval and applicable public-user access requirements remain pending.
2. Codespaces has idle shutdown and development quotas. Select an always-on host with persistent SQLite/media storage, HTTPS and monitored backups. SQLite is suitable for the initial single-server deployment; no Supabase is required.
3. Account recovery, verification, deletion and abuse/cost controls need implementation and end-to-end checks.
4. Discovery still uses synthetic sample content. Live outreach is unavailable. A real discovery source and permitted action transport are needed to deliver the full advertised product. User authorization alone does not enable searching all Instagram posts or messaging arbitrary accounts.
5. Replace the remaining illustrated tutorial panels with current app screenshots. The connection step now uses the actual Instagram sign-in button.
6. Prepare operator-specific privacy, terms, support and data-deletion pages, and the required Meta review materials.
7. Supply a private Android signing key, select a distribution method and test the signed release on devices. Build gates protect packaging; they do not certify commercial readiness.
8. Validate deployment, restore backups, monitor failures and quotas, and complete a security review of the final configuration.

## Release signing configuration

Set DITTO_SIGNING_STORE_FILE, DITTO_SIGNING_STORE_PASSWORD, DITTO_SIGNING_KEY_ALIAS and DITTO_SIGNING_KEY_PASSWORD in the build environment. Keep the key and passwords out of Git. Build with -PdittoApiBaseUrl=https://your-production-host/. Do not use the temporary Codespaces address as the commercial host.

The existing docker-compose.yml remains a development setup with demo mode enabled. Do not publish it as a commercial deployment. Docker runs a single API worker for the current SQLite/import design and disables access logs so authorization query strings are not logged.
