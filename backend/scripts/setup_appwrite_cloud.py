"""Print the isolated candidate schema; --apply creates missing tables only."""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cloud.client import Client, CloudError, DATABASE
from cloud.schema import TABLES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({'databaseId': DATABASE, 'tables': TABLES, 'permissions': [],
                          'note': 'Plan only. No cloud requests or existing data changes.'}, indent=2))
        return
    key = os.getenv('APPWRITE_SETUP_KEY', '')
    if not key:
        raise SystemExit('APPWRITE_SETUP_KEY is required; keep its value out of chat.')
    with Client(key) as client:
        for spec in TABLES:
            path = f'/tablesdb/{DATABASE}/tables/' + spec['tableId']
            try:
                current = client.request('GET', path)
            except CloudError as exc:
                if exc.status != 404:
                    raise
                client.request('POST', f'/tablesdb/{DATABASE}/tables',
                               json={**spec, 'permissions': [], 'rowSecurity': True, 'enabled': True})
                print('Submitted new table:', spec['tableId'])
                continue
            if current.get('$permissions') != [] or current.get('rowSecurity') is not True:
                raise SystemExit('Existing candidate table permissions require review; left unchanged.')
            # No schema repair can delete a column or overwrite existing metadata.
            actual = {c['key']: c for c in current.get('columns', [])}
            for expected in spec['columns']:
                found = actual.get(expected['key'], {})
                for field in ('type', 'required', 'size', 'encrypt'):
                    if field in expected and found.get(field) != expected[field]:
                        raise SystemExit('Existing candidate column differs; left unchanged: ' + expected['key'])
            if any(c.get('status') != 'available' for c in current.get('columns', [])):
                raise SystemExit('Candidate columns are still building. Rerun after they become available.')
            indexes = {i['key']: i for i in current.get('indexes', [])}
            for expected in spec['indexes']:
                found = indexes.get(expected['key'], {})
                if found.get('status') != 'available' or any(found.get(k) != expected[k] for k in ('type', 'columns')):
                    raise SystemExit('Candidate index unavailable or different; left unchanged: ' + expected['key'])
            print('Validated table:', spec['tableId'])
    print('Candidate schema submitted/validated. No SQLite migration or deployment was performed.')


if __name__ == '__main__':
    try:
        main()
    except CloudError:
        raise SystemExit('Appwrite setup failed. Check access/scopes; no key or provider response is printed.') from None
