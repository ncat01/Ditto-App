"""Appwrite Python entrypoint. Trusted runtime key never enters HTTP headers."""
from cloud.api import app


async def dispatch(context, application=app):
    request = context.req
    body = request.body_binary or b''
    if len(body) > 5_300_000:
        return context.res.json({'detail': 'Request too large'}, 413)
    runtime_headers = {str(k).lower(): str(v) for k, v in request.headers.items()}
    key = runtime_headers.get('x-appwrite-key', '')
    if not key:
        return context.res.json({'detail': 'Trusted runtime credentials unavailable'}, 503)
    # The Function platform injects x-appwrite-key. Never expose it to application
    # routing, responses, logs, or a browser-controlled header lookup.
    allowed = {'authorization', 'content-type', 'cookie', 'accept', 'origin'}
    headers = [(k.encode('ascii'), v.encode('latin-1')) for k, v in runtime_headers.items() if k in allowed]
    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': request.method, 'scheme': 'https', 'path': request.path,
             'raw_path': request.path.encode(), 'root_path': '',
             'query_string': (request.query_string or '').encode(), 'headers': headers,
             'client': ('127.0.0.1', 0), 'server': ('ditto', 443), 'ditto.cloud_key': key}
    received = False
    response = {'status': 500, 'headers': [], 'body': bytearray()}
    async def receive():
        nonlocal received
        if not received:
            received = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return {'type': 'http.disconnect'}
    async def send(message):
        if message['type'] == 'http.response.start':
            response['status'] = message['status']
            response['headers'] = message.get('headers', [])
        elif message['type'] == 'http.response.body':
            response['body'].extend(message.get('body', b''))
    try:
        await application(scope, receive, send)
    except Exception:
        # Runtime exception traces can contain sensitive provider data. Return a
        # fixed failure; durable jobs and request status remain queryable.
        return context.res.json({'detail': 'Request failed; check its status before retrying.'}, 503)
    headers = {k.decode('latin-1'): v.decode('latin-1') for k, v in response['headers']
               if k.lower() not in (b'content-length', b'transfer-encoding')}
    return context.res.binary(bytes(response['body']), response['status'], headers)


async def main(context):
    return await dispatch(context)
