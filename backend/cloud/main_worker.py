"""Private asynchronous Function; schedule handles missed execution wakes."""
import asyncio
import json
from cloud.client import Client, CloudError, ident
from cloud.store import Store
from cloud.worker import sweep


async def main(context):
    headers = {str(k).lower(): str(v) for k, v in context.req.headers.items()}
    key = headers.get('x-appwrite-key', '')
    if not key:
        return context.res.json({'detail': 'Trusted runtime credentials unavailable'}, 503)
    def work():
        with Client(key) as client:
            # Only scheduled sweeps process work, including operator cleanup.
            # Immediate wakes are hints: queue due times are always enforced.
            sweep(Store(client), limit=3)
    try:
        await asyncio.to_thread(work)
    except Exception:
        return context.res.json({'detail': 'Worker unavailable; durable queue retained'}, 503)
    return context.res.json({'processed': True})
