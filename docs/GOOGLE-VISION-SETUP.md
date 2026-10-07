# Google Cloud Vision setup for Ditto

This setup is for the app owner once. App users never enter an API key.

1. Open https://console.cloud.google.com/ and create a dedicated project named **Ditto Search**.
2. Open **Billing** and enable billing for this project. Google requires billing even for the free allowance. Do not proceed with payment details if that conflicts with your budget.
3. Open **APIs & Services → Library**, find **Cloud Vision API**, and enable it.
4. Open **APIs & Services → Credentials → Create credentials → API key**.
5. Edit the key. Under **API restrictions**, choose **Restrict key → Cloud Vision API**, then save. This key is only for the hosted backend.
6. In the local VS Code PowerShell terminal, from the outer project folder, run:

   `& '.\Ditto Phoneapp\backend\scripts\save_vision_key.ps1'`

   If already inside the inner source folder, use `& '.\backend\scripts\save_vision_key.ps1'`.

7. Paste the key only into the hidden local prompt, then tell the assistant **saved privately**. Do not put it in chat or source control.

The backend defaults to at most 900 attempted image/frame units per UTC calendar month for this deployment and 40 per account. A video uses five sampled frames. Failed requests consume local allowance conservatively. A dedicated project prevents unrelated applications from sharing the same Google's free allowance; local caps cannot control usage outside Ditto. Google quotas and billing monitoring remain necessary.

Search results are public-web leads, not guaranteed Instagram coverage or verified infringement. Users explicitly consent before an original image or sampled frames go to Google. No arbitrary search result URL is fetched automatically.

Official documentation: https://docs.cloud.google.com/vision/docs/setup
Pricing: https://cloud.google.com/vision/pricing
