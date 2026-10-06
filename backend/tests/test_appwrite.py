from unittest.mock import patch
import httpx
import pytest
from app.config import Settings
from app.providers.appwrite import check_connection, AppwriteUnavailable


def test_read_only_check_keeps_key_in_header_and_redacts_errors():
    settings = Settings(appwrite_api_key='private-test-key')
    def respond(request):
        assert request.method == 'GET'
        assert request.url.path == '/v1/tablesdb'
        assert 'private-test-key' not in str(request.url)
        assert request.headers['X-Appwrite-Key'] == 'private-test-key'
        return httpx.Response(401, json={'message': 'private-test-key'})
    client = httpx.Client(transport=httpx.MockTransport(respond))
    with patch('app.providers.appwrite.get_settings', return_value=settings), patch('app.providers.appwrite.httpx.Client', return_value=client):
        with pytest.raises(AppwriteUnavailable) as error:
            check_connection()
    assert 'private-test-key' not in str(error.value)


def test_endpoint_cannot_send_key_to_another_host():
    settings = Settings(appwrite_api_key='private-test-key', appwrite_endpoint='https://example.com/v1')
    with patch('app.providers.appwrite.get_settings', return_value=settings), patch('app.providers.appwrite.httpx.Client') as client:
        with pytest.raises(AppwriteUnavailable):
            check_connection()
        client.assert_not_called()
