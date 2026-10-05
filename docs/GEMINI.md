# Gemini setup

At https://github.com/settings/codespaces create a Codespaces secret named
`GEMINI_API_KEY`, paste your Google AI Studio key as its value and grant access to
`ncat01/Ditto-App`. Stop and restart the Codespace, then run in its terminal:

```sh
git pull --ff-only
.venv/bin/python backend/scripts/check_gemini.py
```

The check sends generated sample text to Google, prints no secret and reports success
only after a valid draft is returned. Health reports configuration, not verified connectivity.
The authenticated `POST /api/cases/{case_id}/ai-draft` endpoint returns an unsaved
preview for pending cases. Title, recipient, action, tone and existing draft text are
sent to Google; videos are not sent. Evidence, approvals and dispatch are unchanged.
An Android AI draft button is not included in the current APK; use API docs for this endpoint.

Free-tier prompts may be used to improve Google's products. Test with generated sample
content. Keep billing disabled for card-free use. Key/quota/model errors are explicit.
The default model is `gemini-3.5-flash-lite`; `GEMINI_MODEL` may select another available
model. Free quota and access depend on your account.

Never commit the key, place it in the APK or use an Actions secret for Codespaces.
References: https://ai.google.dev/api/generate-content and https://ai.google.dev/gemini-api/docs/pricing.
