"""Small, server-only REST client with redacted failures and private rows."""
from contextlib import contextmanager
import json
import re
import httpx
from app.config import get_settings

DATABASE = '6ac4777b0032876fc1cc'
ACCOUNTS = 'ditto_accounts_v2'
RECORDS = 'ditto_records_v3'
BUDGETS = 'ditto_budgets_v2'


class CloudError(RuntimeError):
    def __init__(self, status=503, code='unavailable'):
        self.status = status
        self.code = code
        super().__init__('Appwrite operation unavailable.')


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,35}', value):
        raise ValueError('Invalid resource identifier.')
    return value


def query(method, attribute=None, values=None):
    obj = {'method': method}
    if attribute is not None:
        obj['attribute'] = attribute
    if values is not None:
        obj['values'] = values
    return json.dumps(obj, separators=(',', ':'))


class Client:
    def __init__(self, key=None, *, transport=None):
        settings = get_settings()
        if settings.appwrite_endpoint.rstrip('/') != 'https://sgp.cloud.appwrite.io/v1':
            raise CloudError()
        key = key or settings.appwrite_api_key.get_secret_value()
        if not key:
            raise CloudError()
        self.http = httpx.Client(base_url=settings.appwrite_endpoint.rstrip('/') + '/',
            timeout=10, follow_redirects=False, transport=transport,
            headers={'X-Appwrite-Project': settings.appwrite_project_id,
                     'X-Appwrite-Key': key})

    def close(self):
        self.http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def request(self, method, path, **kwargs):
        if not path.startswith('/') or path.startswith('//') or '?' in path or '#' in path:
            raise ValueError('Invalid API path.')
        try:
            response = self.http.request(method, path.lstrip('/'), **kwargs)
        except httpx.HTTPError:
            raise CloudError() from None
        if not 200 <= response.status_code < 300:
            code = 'unavailable'
            try:
                value = response.json().get('type')
                if isinstance(value, str) and re.fullmatch('[a-z_]{1,80}', value):
                    code = value
            except (ValueError, AttributeError):
                pass
            raise CloudError(response.status_code, code)
        if response.status_code == 204:
            return {}
        try:
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError()
            return data
        except ValueError:
            raise CloudError() from None

    def base(self, table):
        return f'/tablesdb/{DATABASE}/tables/{ident(table)}/rows'

    def get(self, table, row_id, tx=None):
        params = {'transactionId': tx} if tx else None
        result = self.request('GET', self.base(table) + '/' + ident(row_id), params=params)
        self.private(result)
        return result

    def create(self, table, row_id, data, tx=None):
        body = {'rowId': ident(row_id), 'data': data, 'permissions': []}
        if tx:
            body['transactionId'] = tx
        result = self.request('POST', self.base(table), json=body)
        self.private(result)
        return result

    def patch(self, table, row_id, data, tx=None):
        body = {'data': data}
        if tx:
            body['transactionId'] = tx
        result = self.request('PATCH', self.base(table) + '/' + ident(row_id), json=body)
        self.private(result)
        return result

    def increment(self, table, row_id, column, tx=None, value=1):
        # Transactional increments may return a staged partial row, including
        # for a nonexistent ID. Verify existence and privacy before staging.
        existing = self.get(table, row_id, tx)
        body = {'value': value}
        if tx:
            body['transactionId'] = tx
        result = self.request('PATCH', self.base(table) + '/' + ident(row_id) +
                              '/' + ident(column) + '/increment', json=body)
        if tx and '$permissions' not in result:
            if result.get('$id') != row_id:
                raise CloudError()
            result = {**existing, **result}
        self.private(result)
        return result

    def delete(self, table, row_id, tx=None):
        params = {'transactionId': tx} if tx else None
        return self.request('DELETE', self.base(table) + '/' + ident(row_id), params=params)

    def rows(self, table, queries, *, limit=None):
        cursor = None
        count = 0
        while True:
            filters = list(queries) + [query('limit', values=[100]), query('orderAsc', '$id')]
            if cursor:
                filters.append(query('cursorAfter', values=[cursor]))
            result = self.request('GET', self.base(table), params=[('queries[]', q) for q in filters])
            page = result.get('rows')
            if not isinstance(page, list):
                raise CloudError()
            for row in page:
                self.private(row)
                yield row
                count += 1
                if limit is not None and count >= limit:
                    return
            if len(page) < 100:
                return
            next_cursor = page[-1].get('$id')
            if not next_cursor or next_cursor == cursor:
                raise CloudError()
            cursor = next_cursor

    @staticmethod
    def private(row):
        if not isinstance(row, dict) or row.get('$permissions') != []:
            raise CloudError(503, 'unsafe_permissions')

    @contextmanager
    def transaction(self):
        result = self.request('POST', '/tablesdb/transactions', json={'ttl': 60})
        tx = ident(result['$id'])
        try:
            yield tx
            self.request('PATCH', '/tablesdb/transactions/' + tx, json={'commit': True})
        except Exception:
            try:
                self.request('PATCH', '/tablesdb/transactions/' + tx, json={'rollback': True})
            except CloudError:
                pass
            raise
