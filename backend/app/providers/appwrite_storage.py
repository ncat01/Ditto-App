"""Private server-only storage primitives; caller must check Ditto ownership.

No client permissions are granted: Ditto accounts are not yet Appwrite accounts.
Never expose these methods directly as public routes.
"""
import re
from pathlib import Path
import httpx
from app.config import get_settings
from app.providers.appwrite import AppwriteUnavailable

BUCKET = 'originals'
MAX_BYTES = 20_000_000
CHUNK_BYTES = 5_000_000
EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov'}


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,35}', value):
        raise ValueError('Invalid storage file ID.')
    return value


def client():
    settings = get_settings()
    # Fixed trusted region prevents accidentally forwarding a server key elsewhere.
    if settings.appwrite_endpoint.rstrip('/') != 'https://sgp.cloud.appwrite.io/v1':
        raise AppwriteUnavailable('Unsupported Appwrite storage endpoint.')
    key = settings.appwrite_api_key.get_secret_value()
    if not key:
        raise AppwriteUnavailable('Appwrite key is not configured.')
    return httpx.Client(base_url=settings.appwrite_endpoint.rstrip('/') + '/',
                        timeout=60, follow_redirects=False, headers={
                            'X-Appwrite-Project': settings.appwrite_project_id,
                            'X-Appwrite-Key': key})


def upload_private(path: Path, file_id: str, filename: str | None = None):
    identifier(file_id)
    size = path.stat().st_size
    filename = filename or path.name
    if Path(filename).name != filename or not 0 < size <= MAX_BYTES or Path(filename).suffix.lstrip('.').lower() not in EXTENSIONS:
        raise ValueError('Upload must be an allowed photo/video, at most 20 MB.')
    try:
        with client() as connection, path.open('rb') as source:
            offset = 0
            while offset < size:
                chunk = source.read(min(CHUNK_BYTES, size - offset))
                if not chunk:
                    raise AppwriteUnavailable('Upload source changed while reading.')
                headers = {'Content-Range': f'bytes {offset}-{offset + len(chunk) - 1}/{size}'}
                if offset:
                    headers['X-Appwrite-ID'] = file_id
                response = connection.post(f'storage/buckets/{BUCKET}/files',
                    data={'fileId': file_id}, headers=headers,
                    files={'file': (filename, chunk, 'application/octet-stream')})
                if response.status_code not in (200, 201, 202):
                    raise AppwriteUnavailable('Appwrite storage rejected the upload.')
                result = response.json()
                if result.get('$id') != file_id or result.get('$permissions') != []:
                    raise AppwriteUnavailable('Unexpected storage ID or permissions; do not publish this file.')
                offset += len(chunk)
            if not isinstance(result.get('chunksTotal'), int) or result.get('chunksUploaded') != result.get('chunksTotal'):
                raise AppwriteUnavailable('Storage upload has not completed.')
            return file_id
    except (httpx.HTTPError, ValueError):
        raise AppwriteUnavailable('Storage upload failed. Credentials have not been printed.') from None


def delete_private(file_id: str):
    identifier(file_id)
    try:
        with client() as connection:
            response = connection.delete(f'storage/buckets/{BUCKET}/files/{file_id}')
        if response.status_code not in (204, 404):
            raise AppwriteUnavailable('Appwrite storage rejected file deletion.')
    except httpx.HTTPError:
        raise AppwriteUnavailable('Storage could not be reached.') from None


def download_private(file_id: str) -> bytes:
    identifier(file_id)
    try:
        with client() as connection:
            with connection.stream('GET', f'storage/buckets/{BUCKET}/files/{file_id}/download') as response:
                if response.status_code != 200:
                    raise AppwriteUnavailable('Remote media is unavailable.')
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise AppwriteUnavailable('Remote file exceeds the configured upload limit.')
                return bytes(data)
    except httpx.HTTPError:
        raise AppwriteUnavailable('Remote media could not be reached.') from None
