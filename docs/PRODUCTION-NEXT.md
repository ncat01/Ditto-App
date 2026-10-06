# Commercial launch status

**Implementation prepared; public deployment and commercial launch remain unverified.** Renaming a build or passing local tests cannot certify launch readiness.

Use [the consolidated deployment guide](COMMERCIAL-DEPLOYMENT.md). It replaces repeated Console setup steps with a private runner. The earlier SQLite/Codespaces backend remains intact until a reviewed migration and cutover.

## Implemented

- Isolated Appwrite TablesDB accounts, revocable sessions, recovery/verification, owner checks and durable deletion.
- Private resumable 20 MB uploads, actual image/video pHash comparison, measured cases and private playback.
- Per-user Instagram browser authorization, encrypted credentials, refresh/disconnect and authorized own-media import.
- Optional consented Google web-image search, Gemini previews, explicitly approved SMTP outreach, idempotent receipts and reminders requiring human review. SMTP acceptance is not proof of delivery; interrupted sends are marked unknown rather than automatically resent.
- Android integration, account tutorial with actual Ditto screenshots, Instagram connection button, evidence review and recipient confirmation.
- Private Function staging, live transaction/session/storage probes, guarded source migration, encrypted backup/restore, owner signing key and guarded publication script.
- Security dependency updates. Provider tests use mocks unless a report explicitly says live.

## External completion requirements

| Requirement | Outstanding evidence |
| --- | --- |
| Hosting | Authenticated deployment access; successful Function builds, runtime quota and live staging probes. |
| Instagram | Exact hosted callback, applicable Meta approval and actual public-user device authorization/import. |
| Email | Private SMTP configuration, sender verification and real verification/recovery/outreach inbox tests. |
| Data | Frozen-source inventory, missing-media resolution, reviewed migration and encrypted restore drill. |
| Android | Separately backed-up keystore, stable service origin, signed release and real-device flows. |
| Policies | Owner approval of privacy, retention and backup deletion policy. Draft pages identify Svarsha T and svarsha.t@gmail.com. |
| Operations | Monitoring, backup schedule, restore rehearsal and Education quota review. No paid plan changes are authorized. |
| Discovery | Hashes compare available media; they do not find every Instagram repost. Google search requires separately approved configuration. Links and similarity scores do not establish infringement. |

The launch script requires actual operator evidence. Broad automatic Instagram discovery, face recognition and ASR are not delivered features.
