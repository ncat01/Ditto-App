# Ditto — Content credit and evidence review

Ditto 1.8.9 is the existing Kotlin Compose Android app with a hosted FastAPI/PostgreSQL backend. Users sign in directly; they do not enter API keys or backend URLs. Release builds exclude synthetic accounts, reels, cases and offline mode.

**The known copied-Reel acceptance test failed:** the search completed but did not find the specified copy. The release is downloadable for further validation; public commercial launch is not certified.

Choose a saved original, upload a file you own, or import your own Reel from a connected professional Instagram account. The selected original opens **Find copies**. Confirm sharing the image or selected video frames to start a real reverse web search. Search progress and results are saved, so you can return Home and reopen the original later. If you already have a suspected repost, **Compare a suspected repost** checks its file against your original and creates a private review case.

SerpApi Google Lens searches exact and visually similar images on indexed public pages. It cannot guarantee coverage of every public Instagram Reel. A completed search with no indexed matches does not establish that no repost exists. Failed searches and unreadable results remain errors. Similarity and source links require human review and do not establish infringement.

- Package: `com.ditto.app`; version 1.8.9/code 18.
- API: https://ditto-api-production-7e7f.up.railway.app
- Signed APK/AAB: [DITTO-1.8.9-release.apk](apk/DITTO-1.8.9-release.apk) and [DITTO-1.8.9-release.aab](apk/DITTO-1.8.9-release.aab), Android 8+, target API 36.
- Owner: Svarsha T. Support: svarsha.t@gmail.com.
- Runtime: `android/app/src/main` and `backend/app`. Historical examples remain under `eval` and are excluded from release.

Current validation: **129 backend tests and 33 Android unit tests pass**. The signed 1.8.9 APK/AAB builds are complete. The latest Railway deployment succeeded; live health returns HTTP 200 and a connected database.

Version 1.8.9 makes Find copies the primary action, automatically selects imported originals, restores saved searches, and gives clear queued/running/completed/failed states. Lost submission responses recover the exact saved request; explicit retries reuse its request ID to prevent duplicate searches. Confirmed request rejection clears the pending state and leaves direct comparison available. Connection recovery and logout handling keep stale network errors and previous-account data out of customer screens. Live restoration of earlier saved web-search results is verified and does not run or charge another provider query.

The real original Reel `DeIBHC7NOcX` imported successfully. Its two earlier saved searches each contain 50 source URLs, but neither includes the known suspected copy `DeLwnWiz9lW`. One fresh normal search completed with 50 source URLs, including six Instagram links, and zero exact matches. It returned neither the original nor the known copy. This confirms that the current provider search missed this repost. The video search used ten provider query units; the owner's current allowance is 20 units/month and all 20 are now used. The live global cap is 225 units/month.

Reviewed outreach opens in the phone's email app; Ditto does not claim drafts were sent or delivered. Recovery and verification email are unavailable on the current host because no sender is configured. Non-role professional Instagram customers still require Meta App Review, Advanced Access and publishing before they can authorize this integration. Signed downloads and a working hosted core do not certify public commercial launch.

See [progress](PROGRESS.md), [Instagram approval steps](docs/INSTAGRAM_SIGN_IN.md) and [remaining launch requirements](BLOCKERS.md). Keep provider credentials, uploads, databases and signing keys out of source control and APKs.
