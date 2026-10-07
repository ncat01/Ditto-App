# SerpApi reverse search

1. Register at https://serpapi.com/users/sign_up and choose the Free plan.
2. Open https://serpapi.com/manage-api-key and copy your private API key.
3. In local VS Code PowerShell, from the outer workspace, run:

   `& '.\Ditto Phoneapp\backend\scripts\save_serpapi_key.ps1'`

4. Paste the key only into the hidden prompt. Reply "saved privately".

The backend uses SERPAPI_API_KEY. Ordinary users never configure credentials.
Search requires explicit consent to share an image or five sampled video frames
with SerpApi for Google Lens processing. Provider uploads are not guaranteed to
be immediately deleted; do not promise ZeroTrace on the Free plan.

Ditto reserves at most 225 attempted frame/image searches per UTC month,
10 per account, and 45 per hour across the deployment. SerpApi's free allowance
is 250 successful searches per provider billing month; use a dedicated account
and keep paid renewal disabled. Provider limits still apply across calendar
boundaries and outside Ditto. Failed local attempts count conservatively.

Public web results are unverified leads. Coverage of every Instagram Reel is
not guaranteed. Google Cloud billing and a Google Cloud Vision key are no longer
required for this search integration.

References: https://serpapi.com/pricing and https://serpapi.com/google-lens-upload-an-image
