# Ditto — Content credit and evidence review

The existing Kotlin Compose Android app uses a hosted FastAPI/PostgreSQL backend. Users sign in directly; no API keys or backend URLs are entered. Production excludes synthetic accounts, reels, cases and offline mode.

Upload originals or authorize your professional Instagram account, then run a reverse web search or submit a suspected copy for measured image/video comparison. SerpApi Google Lens searches images and selected video frames; it cannot guarantee coverage of every Instagram Reel. Database-backed jobs create private review cases only for results the user asks Ditto to examine. Similarity does not establish infringement.

Reviewed outreach opens in the phone's email app. Ditto does not claim drafts were sent or delivered. Optional SMTP requires exact recipient/message approval and never retries an uncertain attempt automatically. Recovery email needs a configured sender.

- Package: com.ditto.app
- API: https://ditto-api-production-7e7f.up.railway.app
- Signed APK/AAB: apk/DITTO-1.8.5-release.apk and .aab
- Owner: Svarsha T. Support: svarsha.t@gmail.com.
- Runtime: android/app/src/main and backend/app. Historical examples are preserved under eval and excluded from release.

Backend validation: 95 passing tests. Live verification covers empty signup, private media, queued comparison/review cases, token rotation, and reverse image search. Android 1.8.5 adds the commercial visual identity, guided connection flow, focused empty home, and touch-reactive aura background. See [evidence](docs/evidence/railway-processing-release.txt), [progress](PROGRESS.md) and [remaining launch requirements](BLOCKERS.md). Working core and signing do not certify public commercial launch.

Keep provider credentials, uploads, databases and signing keys out of source control and APKs.
