# Production work in progress

The first hosted version will use SQLite, as requested. Supabase is not used.
SQLite is already part of both the Android app (Room) and FastAPI backend, and
requires no database API key. These are separate databases; Android currently
does not synchronize with the backend.

## Hosting prerequisite

Activate Azure for Students through https://education.github.com/pack or
https://azure.microsoft.com/free/students. Use the account you want to own the
deployment. Complete student verification, then check that an active Azure for
Students subscription appears at https://portal.azure.com under Subscriptions.
The offer advertises $100 credit for eligible students; credits and free quotas
are not unlimited permanent hosting.

Do not send Microsoft or GitHub passwords, verification codes, or recovery codes.
Deployment authorization will use interactive sign-in once the account is ready.

## SQLite hosting requirements

- One persistent backend host; keep the database and private videos on a durable
  local disk, never an ephemeral deployment filesystem.
- HTTPS access to the API and authenticated ownership checks on all private data.
- Consistent SQLite backups plus matching media backups, and a restore check.
- One follow-up scheduler, with persisted deadlines and approved action records.
- Connect the Android client to authenticated backend APIs before calling it a
  connected production release.

## Credentials, one at a time

Hosting authorization comes first. Then configure only providers with implemented
adapters, verify them, and report actual connectivity. No secret credentials have
been added and none are bundled in the APK. Meta developer permissions and user
OAuth consent are required separately; an API key does not grant access to every
Instagram post or authorize reporting. Free AI tiers have quotas and their own
data-use terms; choose them before sending private content.

Firebase was considered: Spark has free quotas for Firestore and some auth
services, but Cloud Storage for video requires a billing-enabled Blaze plan.
SQLite was selected to preserve the existing relational backend.

## Current visual build

Version 1.2.0-sunset-demo-debug introduces Caveat handwriting, Space Grotesk
headings, DM Sans body copy, an original quotation-shaped d logo, and an off-white,
charcoal, pink, peach, coral and sunrise-yellow theme. Fonts are bundled for
offline use; redistribution licenses are in docs/font-licenses.
This APK is still a debug-signed offline demo.
