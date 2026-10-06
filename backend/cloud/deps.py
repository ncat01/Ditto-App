from fastapi import Request
from cloud.client import Client
from cloud.store import Store


def get_store(request: Request):
    factory = getattr(request.app.state, 'client_factory', None)
    with (factory() if factory else Client(request.scope.get('ditto.cloud_key'))) as client:
        yield Store(client)
