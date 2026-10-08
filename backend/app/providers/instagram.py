"""Read-only Instagram Login adapter. Never publishes or sends messages.

The deployment token is not exposed through a shared account endpoint. Account
binding and per-user OAuth storage must precede Android integration.
"""
import httpx
from pydantic import BaseModel, Field, ValidationError
from app.config import get_settings

class InstagramUnavailable(Exception):
    pass

class Profile(BaseModel):
    user_id: str = Field(pattern=r'^\d+$')
    username: str = Field(min_length=1, max_length=128)

class MediaItem(BaseModel):
    id: str = Field(pattern=r'^\d+$')
    media_type: str
    caption: str = ''
    permalink: str = ''
    timestamp: str = ''
    media_url: str = ''

class InstagramReader:
    def __init__(self, token=None):
        settings = get_settings()
        self._token = token if token is not None else settings.meta_access_token.get_secret_value()
        self._base = 'https://graph.instagram.com/' + settings.meta_api_version

    def _get(self, path, params):
        if not self._token:
            raise InstagramUnavailable('Connect your Instagram account in Ditto first.')
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                response = client.get(self._base + path, params=params,
                    headers={'Authorization': 'Bearer ' + self._token})
            if response.status_code != 200:
                # Provider bodies can contain private data. Return only fixed messages.
                code = None
                try: code = response.json().get('error', {}).get('code')
                except (ValueError, AttributeError): pass
                if code == 190:
                    message = 'Your Instagram connection expired. Reconnect Instagram in Ditto.'
                elif response.status_code == 429 or code in (4, 17, 32, 613):
                    message = 'Instagram rate limit reached. Try later.'
                elif response.status_code in (400, 401, 403):
                    message = 'Instagram did not allow access to this account. Reconnect and approve the requested access. If it continues, contact Ditto support.'
                else:
                    message = 'Instagram is temporarily unavailable. Please try again later.'
                raise InstagramUnavailable(message)
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise InstagramUnavailable('Instagram could not be reached or returned an invalid response.') from None

    def profile(self):
        try:
            return Profile.model_validate(self._get('/me', {'fields': 'user_id,username'}))
        except ValidationError:
            raise InstagramUnavailable('Instagram returned no usable Creator profile.') from None

    def media(self, user_id, limit=5):
        if not str(user_id).isdigit():
            raise InstagramUnavailable('Invalid Instagram account identifier.')
        result = self._get('/' + str(user_id) + '/media', {
            'fields': 'id,caption,media_type,permalink,timestamp', 'limit': max(1, min(limit, 25))})
        try:
            data = result['data']
            if not isinstance(data, list): raise TypeError()
            return [MediaItem.model_validate(item) for item in data]
        except (KeyError, TypeError, ValidationError):
            raise InstagramUnavailable('Instagram returned no usable media list.') from None

    def media_item(self, media_id):
        if not str(media_id).isdigit():
            raise InstagramUnavailable('Invalid Instagram media identifier.')
        try:
            return MediaItem.model_validate(self._get('/' + str(media_id), {
                'fields': 'id,caption,media_type,media_url,permalink,timestamp'}))
        except ValidationError:
            raise InstagramUnavailable('Instagram returned no usable media record.') from None

    def download_video(self, item):
        from urllib.parse import urlsplit
        url = urlsplit(item.media_url)
        host = (url.hostname or '').lower()
        allowed = any(host.endswith('.' + domain) for domain in ('cdninstagram.com', 'fbcdn.net'))
        if item.media_type != 'VIDEO':
            raise InstagramUnavailable('Choose a video or Reel. Image and carousel import is not available yet.')
        if url.scheme != 'https' or not allowed or url.username or url.password or url.port not in (None,443):
            raise InstagramUnavailable('Instagram media download address is unsupported.')
        try:
            # Never forward the API bearer token to a CDN; never follow redirects.
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                with client.stream('GET',item.media_url) as response:
                    if response.status_code != 200:
                        raise InstagramUnavailable('Instagram video download unavailable. Refresh the post list.')
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 25*1024*1024:
                            raise InstagramUnavailable('Instagram video exceeds the 25 MB import limit.')
            if not data:
                raise InstagramUnavailable('Instagram returned an empty video.')
            return bytes(data)
        except httpx.HTTPError:
            raise InstagramUnavailable('Instagram video download could not be completed.') from None
