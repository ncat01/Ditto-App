"""Server-only Appwrite connection. Never replaces SQLite implicitly."""
from urllib.parse import urlsplit
import httpx
from app.config import get_settings


class AppwriteUnavailable(RuntimeError):
    pass


def check_connection() -> None:
    settings = get_settings()
    endpoint = settings.appwrite_endpoint.rstrip('/')
    parsed = urlsplit(endpoint)
    if (parsed.scheme != 'https' or parsed.hostname != 'sgp.cloud.appwrite.io'
            or parsed.path != '/v1' or parsed.query or parsed.fragment
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise AppwriteUnavailable('Unsupported Appwrite endpoint.')
    key = settings.appwrite_api_key.get_secret_value()
    if not key:
        raise AppwriteUnavailable('Appwrite key is not configured.')
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get(endpoint + '/tablesdb', headers={
                'X-Appwrite-Project': settings.appwrite_project_id,
                'X-Appwrite-Key': key,
            })
        if response.status_code != 200:
            raise AppwriteUnavailable('Appwrite rejected the connection; check the project and databases.read scope.')
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get('databases'), list):
            raise AppwriteUnavailable('Unexpected Appwrite response.')
    except (httpx.HTTPError, ValueError):
        raise AppwriteUnavailable('Appwrite could not be reached or returned an invalid response.') from None
