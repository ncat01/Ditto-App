"""Add the Originals schema without deleting data or changing permissions.

Use a temporary APPWRITE_SETUP_KEY with columns.read/write,
indexes.read/write and tables.read. Revoke it after setup.
"""
import os
import time
import httpx

ENDPOINT = 'https://sgp.cloud.appwrite.io/v1'
PROJECT = '6ac46d45002b91afdd73'
DATABASE = '6ac4777b0032876fc1cc'
TABLE = '6ac478400035747f156f'
COLUMNS = {'owner_id': 36, 'title': 200, 'file_id': 36,
           'media_type': 16, 'fingerprint': 2048, 'source_url': 2048}


def request(client, method, path, **kwargs):
    response = client.request(method, ENDPOINT + path, **kwargs)
    if response.status_code not in (200, 201, 202):
        raise RuntimeError(f'Appwrite returned HTTP {response.status_code}. Check the setup key scopes and resource IDs. No existing data was deleted.')
    return response.json()


def setup(client):
    base = f'/tablesdb/{DATABASE}/tables/{TABLE}'
    request(client, 'GET', base)
    # Fetch each expected column directly: avoids pagination accidentally hiding it.
    for key, size in COLUMNS.items():
        response = client.get(ENDPOINT + base + '/columns/' + key)
        required = key in ('owner_id', 'title', 'file_id', 'media_type')
        if response.status_code == 404:
            request(client, 'POST', base + '/columns/string', json={
                'key': key, 'size': size, 'required': required, 'array': False,
                'encrypt': False,
            })
            print('Created column: ' + key)
        elif response.status_code == 200:
            column = response.json()
            if (column.get('type') != 'string' or column.get('size') != size
                    or column.get('required') != required or column.get('array', False)
                    or column.get('encrypt', False)):
                raise RuntimeError('Existing column differs from the schema: ' + key + '. Left unchanged.')
            print('Kept existing column: ' + key)
        else:
            raise RuntimeError(f'Unable to inspect {key}: HTTP {response.status_code}.')
    deadline = time.monotonic() + 90
    while True:
        columns = [request(client, 'GET', base + '/columns/' + key) for key in COLUMNS]
        if any(c.get('status') == 'failed' for c in columns):
            raise RuntimeError('A column failed to build. Check Appwrite Console.')
        if all(c.get('status') == 'available' for c in columns):
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Columns are still building. Rerun this script later; existing columns will be preserved.')
        time.sleep(2)
    response = client.get(ENDPOINT + base + '/indexes/by_owner')
    if response.status_code == 404:
        request(client, 'POST', base + '/indexes', json={
            'key': 'by_owner', 'type': 'key', 'columns': ['owner_id'], 'orders': ['ASC'],
        })
        print('Owner index submitted. Check Console for its available status.')
    elif response.status_code == 200:
        index = response.json()
        if index.get('columns') != ['owner_id'] or index.get('type') != 'key':
            raise RuntimeError('Existing owner index differs; left unchanged.')
        if index.get('status') == 'failed':
            raise RuntimeError('Owner index failed; check Console.')
        print('Kept owner index. Status: ' + str(index.get('status')))
    else:
        raise RuntimeError(f'Unable to inspect owner index: HTTP {response.status_code}.')


if __name__ == '__main__':
    key = os.getenv('APPWRITE_SETUP_KEY')
    if not key:
        raise SystemExit('APPWRITE_SETUP_KEY is missing. Store it privately as a Codespaces secret; do not paste it in chat.')
    try:
        with httpx.Client(timeout=20, follow_redirects=False, headers={
            'X-Appwrite-Project': PROJECT, 'X-Appwrite-Key': key,
        }) as client:
            setup(client)
    except httpx.HTTPError:
        raise SystemExit('Appwrite connection failed. Credentials have not been printed.') from None
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None
    print('Originals schema prepared. Existing rows and permissions unchanged. Revoke the temporary setup key now.')
    print('This does not migrate SQLite or deploy the backend.')
