# Launch status — 2026-10-07

The hosted core and signed Android release work; public commercial launch is not certified.

- Instagram: owner reports "insufficient developer role". An accepted Meta account role is required while the app is in development. Public permissions/review remain unverified. The owner confirmed saving the HTTPS callback; its exact redirect was tested.
- Email: owner declined Gmail App Password setup. Outreach opens a reviewed draft in the user's email app; Ditto cannot confirm sending/delivery. Recovery and verification email require an authenticated sender. Optional SMTP remains disabled.
- Automated discovery: SerpApi Google Lens reverse image search is live and verified; video searches selected frames. The free quota and Ditto's usage caps are suitable for the initial small cohort, but results cannot guarantee coverage of every Instagram Reel.
- Face/manipulation and infringement classification: unavailable. Actual image/video pHash similarity requires human review.
- Hosting continuity: Railway uses the owner's remaining trial credit. No paid upgrade is authorized. Trial usage, backups and restore verification need coverage for dependable commercial operation.
- Architecture: PostgreSQL queue with a background worker in the API service and private persistent-volume media. The brief's separate Redis worker/scheduler and S3 stack has not been deployed.
- Device acceptance: signed 1.8.4 was installed on the Vivo V40 and reached Instagram authorization. The redesigned signed 1.8.5 passed visual navigation on the emulator and installed successfully on a Realme CPH2585. The Realme was locked during capture, so final owner visual acceptance on that handset remains pending.
- Signing: owner key outside source at ~/ditto-keystore. Separate secure backup remains an operator task.
- Store/public release approval is not performed.

Verified: live PostgreSQL/HTTPS API, empty signup, private originals/candidates, cross-user denial, queued measured comparison creating a real review case, reverse image search, refresh rotation and account/media persistence across API restart. Temporary verification content was removed.
