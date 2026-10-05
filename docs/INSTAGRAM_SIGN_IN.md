# Instagram sign-in

Ditto users connect their own Creator or Business account using Continue with Instagram, in the signup guide, Profile or Originals. Authorization opens in the external browser; return to Ditto and use Refresh connection if needed. The Android app never receives the Instagram app secret or Instagram access token.

The server stores each user's token encrypted, binds the authorization link to the signed-in Ditto session and browser, and consumes the link once. Disconnect removes the stored token; imported originals remain. Users can separately revoke the grant in Instagram Apps and websites.

## Operator setup

Set INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, PUBLIC_BASE_URL and TOKEN_ENCRYPTION_KEY on the hosted backend. Register PUBLIC_BASE_URL/api/integrations/instagram/callback in Meta. PUBLIC_BASE_URL must be the same HTTPS origin used in the Android backend settings. Production requires TOKEN_ENCRYPTION_KEY from persistent secret storage. Codespaces development can initialize its private .ditto-data/token-encryption.key using backend/scripts/initialize_token_storage.py. Back up the key separately; losing it makes saved connections unreadable.

The earlier META_ACCESS_TOKEN and bind_instagram.py setup are developer checks only; the user-facing import API now requires a per-user OAuth connection.

## Release limits

This is an integration build, not a commercial release. A working sign-in must still be verified against Meta. Public users need the applicable Meta review and access approval. Codespaces is a development environment. Imports access the connected user's own media; this does not provide platform-wide repost discovery. The current discovery and outgoing action system remains a sandbox.
