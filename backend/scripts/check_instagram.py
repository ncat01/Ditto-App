"""Run in Codespaces. Does not print credentials, usernames or post contents."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers.instagram import InstagramReader, InstagramUnavailable
try:
    reader = InstagramReader()
    profile = reader.profile()
    posts = reader.media(profile.user_id)
except InstagramUnavailable as exc:
    raise SystemExit('Instagram check failed: ' + str(exc))
print('Instagram connected: Creator profile and own-media access verified.')
print('Posts returned in sample: ' + str(len(posts)) + ' (zero is valid for a new account).')
print('No posts were published and no messages were sent.')
