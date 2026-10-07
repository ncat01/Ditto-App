# Ditto — Content credit and evidence review

The existing Kotlin Compose Android app uses a hosted FastAPI/PostgreSQL backend. Users sign in directly; no API keys or backend URLs are entered. Production excludes synthetic accounts, reels, cases and offline mode.

Upload originals or authorize your professional Instagram account, then run a reverse web search or submit a suspected copy for measured image/video comparison. SerpApi Google Lens searches images and selected video frames; it cannot guarantee coverage of every Instagram Reel. Database-backed jobs create private review cases only for results the user asks Ditto to examine. Similarity does not establish infringement.

Reviewed outreach opens in the phone's email app. Ditto does not claim drafts were sent or delivered. Optional SMTP requires exact recipient/message approval and never retries an uncertain attempt automatically. Recovery email needs a configured sender.

- Package: com.ditto.app
- API: https://ditto-api-production-7e7f.up.railway.app
- Signed APK/AAB: apk/DITTO-1.8.8-release.apk and .aab (Android 8+, target API 36)
- Owner: Svarsha T. Support: svarsha.t@gmail.com.
- Runtime: android/app/src/main and backend/app. Historical examples are preserved under eval and excluded from release.

Backend validation: 120 passing tests; Android: 18 passing unit tests, release lint, R8, signed APK and signed AAB builds. Live verification covers empty signup, private media, queued comparison/review cases, token rotation, queued reverse image search, request deduplication and restored search results. Version 1.8.8 fixes empty exact-match responses aborting search, lets searches continue after leaving the screen, restores saved results, adds Home navigation to comparisons, removes technical labels and preserves the measured percentage for submitted copies. Case cards and filters use actual content similarity. Image evidence opens as images, while video evidence retains playback. The colorful identity, guided connection flow and touch-reactive aura background remain. See [progress](PROGRESS.md), [Instagram approval steps](docs/INSTAGRAM_SIGN_IN.md) and [remaining launch requirements](BLOCKERS.md). Working core and signing do not certify public commercial launch.

Keep provider credentials, uploads, databases and signing keys out of source control and APKs.
