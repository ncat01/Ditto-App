from unittest.mock import patch
import httpx
import pytest
from app.providers.appwrite_storage import upload_private, delete_private
from app.providers.appwrite import AppwriteUnavailable


def test_chunks_and_private_permissions(tmp_path):
    path = tmp_path / 'sample.mp4'
    path.write_bytes(b'a' * 5_000_001)
    calls = []
    def respond(request):
        calls.append(request)
        assert request.method == 'POST'
        assert request.url.path == '/v1/storage/buckets/originals/files'
        assert b'read("any")' not in request.content
        return httpx.Response(201, json={'$id': 'sample', '$permissions': [],
            'chunksTotal': 2, 'chunksUploaded': len(calls)})
    connection = httpx.Client(base_url='https://sgp.cloud.appwrite.io/v1/', transport=httpx.MockTransport(respond))
    with patch('app.providers.appwrite_storage.client', return_value=connection):
        assert upload_private(path, 'sample') == 'sample'
    assert calls[0].headers['Content-Range'] == 'bytes 0-4999999/5000001'
    assert calls[1].headers['X-Appwrite-ID'] == 'sample'


def test_rejects_public_permissions(tmp_path):
    path = tmp_path / 'sample.jpg'
    path.write_bytes(b'sample')
    connection = httpx.Client(base_url='https://sgp.cloud.appwrite.io/v1/', transport=httpx.MockTransport(
        lambda r: httpx.Response(201, json={'$id': 'sample', '$permissions': ['read("any")']})))
    with patch('app.providers.appwrite_storage.client', return_value=connection):
        with pytest.raises(AppwriteUnavailable):
            upload_private(path, 'sample')


def test_rejects_large_file_and_path_injection(tmp_path):
    path = tmp_path / 'sample.mp4'
    with path.open('wb') as file:
        file.truncate(20_000_001)
    with patch('app.providers.appwrite_storage.client') as connection:
        with pytest.raises(ValueError): upload_private(path, 'sample')
        with pytest.raises(ValueError): delete_private('../other')
        connection.assert_not_called()
