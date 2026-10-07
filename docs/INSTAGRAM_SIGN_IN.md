# Instagram connection and public customer access

Ditto uses Instagram API with Instagram Login. Customers connect their own **Creator or Business professional account**; this API does not support personal Instagram accounts. This login flow does not require a linked Facebook Page. See [Meta's Instagram Login collection](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login).

Customers sign in to Ditto, choose **Continue with Instagram** in the signup guide, Profile or Originals, and approve access in Instagram's browser screen. Returning to Ditto automatically checks connection status and displays **Instagram connected** with the connected username. No API keys, server URL or tester setup belongs in the normal customer flow. **Switch Instagram account** opens browser sign-out so another account can authorize.

The backend stores each customer's Instagram token encrypted. Authorization links are bound to the signed-in Ditto session and browser, expire after ten minutes, and can be consumed once. The APK never receives the app secret or Instagram access token. Disconnect removes Ditto's stored connection; imported originals remain until separately deleted. Customers can revoke the grant in Instagram's Apps and websites settings.

## Required Meta configuration for the operator

The Railway backend origin is:

```text
https://ditto-api-production-7e7f.up.railway.app
```

Register this exact OAuth redirect URL in Meta's **Instagram API setup with Instagram login → Business login settings**:

```text
https://ditto-api-production-7e7f.up.railway.app/api/integrations/instagram/callback
```

Keep `INSTAGRAM_APP_ID`, `INSTAGRAM_APP_SECRET`, `PUBLIC_BASE_URL` and `TOKEN_ENCRYPTION_KEY` in backend secret configuration. `PUBLIC_BASE_URL` must equal the HTTPS origin above. Keep the encryption key persistent and back it up privately: losing it makes saved connections unreadable.

The current authorization request asks only for `instagram_business_basic`, which supports the connected account and its own media. Do not request publishing, comments or messaging permissions unless the app implements and needs those capabilities. Meta lists the current scope names in its [official Instagram Login collection](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login).

## Removing the developer/tester restriction

An installed APK and working backend do not grant Meta production access. **Insufficient developer role** means Meta has rejected the account at its authorization gate; a refresh or APK rebuild cannot grant that permission.

Before customers without an app role can authorize:

1. Complete the required app details and the privacy and data-deletion URLs in the Meta App Dashboard. Complete Business Verification and any other prerequisites that Meta requires for this app.
2. In **App Review / Permissions and features**, request **Advanced Access** for `instagram_business_basic` through Meta App Review. Supply a reviewer-accessible build, test instructions and a screencast showing Ditto signup, Instagram consent, connected username, own-media import and disconnect. Request only the permissions used by Ditto.
3. Wait for Meta to approve the requested access. Publish the app or switch it to **Live**, according to the publishing controls shown for this app in the dashboard. Live/published status alone does not replace permission approval.
4. Test the complete connection and import flow with a professional account that has no administrator, developer or tester role. Verify that its owner can approve access and Ditto updates to Connected.

Standard Access is intended for app-role accounts; Advanced Access is needed for non-role customers. These are operator steps, not steps every customer should repeat. **This document does not assert that Ditto has received Meta approval or that public Instagram authorization has been verified.** Check the actual approval and publishing status in the app's dashboard.

Official operator references: [Meta access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels/), [Instagram App Review](https://developers.facebook.com/docs/instagram-platform/app-review/), [app modes and publishing](https://developers.facebook.com/docs/development/build-and-test/app-modes/), and [Instagram Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login/). Meta may require a developer login to read these pages.

## What repost search can find

Instagram connection imports the connected customer's own media. It does not grant an API that searches every public Instagram post.

Ditto separately uses SerpApi Google Lens to search publicly indexed web pages, explicitly querying [exact matches](https://serpapi.com/google-lens-exact-matches-api) and [visual matches](https://serpapi.com/google-lens-visual-matches-api). Videos are searched using five sampled frames. Customers consent before originals or frames are sent to the search provider. Results are leads to review, rather than verified infringement findings.

**Ditto cannot promise to find every public Reel or every account reposting a video.** A public post can be absent from the search index. An empty search does not establish that no repost exists. When a suspected copy is available, customers can upload it for direct comparison and review the source, dates, credit and permission.
