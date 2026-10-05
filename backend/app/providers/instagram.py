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

class InstagramReader:
    def __init__(self):
        settings = get_settings()
        self._token = settings.meta_access_token.get_secret_value()
        self._base = 'https://graph.instagram.com/' + settings.meta_api_version

    def _get(self, path, params):
        if not self._token:
            raise InstagramUnavailable('META_ACCESS_TOKEN is not configured.')
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
                    message = 'Instagram token invalid or expired. Generate a new token and update the Codespaces secret.'
                elif response.status_code == 429 or code in (4, 17, 32, 613):
                    message = 'Instagram rate limit reached. Try later.'
                elif response.status_code in (400, 401, 403):
                    message = 'Instagram request denied. Check token, Instagram tester invitation and instagram_business_basic permission.'
                else:
                    message = 'Instagram service or API version unavailable. Try later or check META_API_VERSION.'
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
