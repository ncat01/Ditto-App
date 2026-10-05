# Instagram import ? connected test 1.4.0

The operator stores the Instagram Login token as a Codespaces secret named
`META_ACCESS_TOKEN`, granting access to `ncat01/Ditto-App`. Stop and restart
Codespaces after changing secrets. Check access with:

```sh
.venv/bin/python backend/scripts/check_instagram.py
```

## Bind your Creator account to a Ditto account

Pull the latest source, then stop and restart Codespaces to load the new API code.
Run this in the Codespaces Terminal to create a new Ditto login and bind Instagram:

```sh
.venv/bin/python backend/scripts/bind_instagram.py --create
```

Enter the email and password you want for Ditto. Password input is hidden. To use
an existing Ditto server account, omit `--create`. This logs in via the local API,
checks your Instagram profile and writes an operator-owned binding file under
`.ditto-data/`. The temporary Ditto session is revoked. No credential is printed
or written to the binding file. The Instagram token stays in Codespaces secrets.

Sign into Android **Connected test** with the same Ditto email/password and your
forwarded HTTPS URL. In **Originals**, choose **Load Instagram posts**, then
**Import video**. Latest 25 posts are listed; only video/Reel imports up to 25 MB
are supported. Re-importing the same post returns its existing library item.
Private playback uses account-scoped server APIs. Publication time is retained;
five real frames are fingerprinted. Discovery still uses a synthetic corpus.

The deployment token is bound to one Ditto account, not exposed to other accounts.
Changing the token requires re-running the binding script. Multi-user Instagram
OAuth and encrypted per-user token storage remain future production work.
The current server must use one worker; imports are serialized within that worker.

## Gemini drafting

For a pending case choose **Draft with Gemini**, read the data-sharing prompt,
generate a preview, edit it, then **Save draft**. The existing saved draft is
unchanged until Save succeeds. Actions still require a separate approval and
outreach stays sandboxed. No Gemini result changes evidence or policy scores.
A title, recipient and current draft are sent to Google; no video is sent.

No publishing, messaging or arbitrary repost search is enabled by Instagram import.
API version defaults to `v25.0`. Tokens expire; regenerate, update the secret and
rebind when necessary. Webhooks and publishing the Meta app are not needed for
this read-only tester workflow.
