# Launch status — 2026-10-08

The hosted core and signed Android release work; public commercial launch is not certified.

- Instagram: owner reports "insufficient developer role". An accepted Meta account role is required while the app is in development. Public permissions/review remain unverified. The owner confirmed saving the HTTPS callback; its exact redirect was tested.
- Email: owner declined Gmail App Password setup. Outreach opens a reviewed draft in the user's email app; Ditto cannot confirm sending/delivery. Recovery and verification email require an authenticated sender. Optional SMTP remains disabled.
- Automated discovery: SerpApi Google Lens exact and visual reverse image search is live and verified; video searches five sampled frames. Searches have persistent progress/results and survive leaving the Android screen. Budget: 225 provider queries/month globally and 10/account/month by default; an image uses two queries and a video uses ten. These quotas may need adjustment for 25 active users. Results cannot guarantee coverage of every Instagram Reel. No known copied-Reel discovery acceptance test has been completed.
- Face/manipulation and infringement classification: unavailable. Actual image/video pHash similarity requires human review.
- Hosting continuity: Railway uses the owner's remaining trial credit. No paid upgrade is authorized. Trial usage, backups and restore verification need coverage for dependable commercial operation.
- Architecture: PostgreSQL queue with a background worker in the API service and private persistent-volume media. The brief's separate Redis worker/scheduler and S3 stack has not been deployed.
- Device acceptance: signed 1.8.4 was installed on the Vivo V40 and reached Instagram authorization. The redesigned signed 1.8.5 passed visual navigation on the emulator and installed successfully on a Realme CPH2585. Signed 1.8.8 passed emulator installation, actual image previews, accurate 100% case-card similarity and returning Home from comparison. The physical phone is disconnected, so final handset acceptance remains pending.
- Signing: the signed 1.8.8 APK/AAB retain the existing owner certificate. Local signing material is outside tracked source in .ditto-data/release-signing. Separate secure backup remains an operator task.
- Store/public release approval is not performed.

Verified: live PostgreSQL/HTTPS API, empty signup, private originals/candidates, cross-user denial, queued measured comparison creating a real review case, exact/visual reverse image search, duplicate-search protection, saved-result restoration, refresh rotation and account/media persistence across API restart. Temporary API verification content was removed. All 120 backend tests and 18 Android unit tests pass; signed 1.8.8 APK/AAB target API 36 and native libraries pass 16 KB alignment checks. Public Meta access, email delivery, exhaustive repost coverage, production hosting continuity and store approval remain unverified.
