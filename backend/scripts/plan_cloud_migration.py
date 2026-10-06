"""Read-only migration inventory from a consistent SQLite snapshot. No cloud writes."""
import argparse
import json
import re
import sqlite3
from pathlib import Path


def inventory(path):
    path = path.resolve(strict=True)
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as source:
        with sqlite3.connect(':memory:') as snapshot:
            source.backup(snapshot)
            tables = [r[0] for r in snapshot.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            if any(not re.fullmatch('[a-z_]+', t) for t in tables):
                raise ValueError('Unexpected table name; migration requires review.')
            counts = {t: snapshot.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0] for t in tables}
            account_count = 0
            invalid_accounts = 0
            if 'users' in tables:
                for identity, email, salt, hashed in snapshot.execute('SELECT id, email, salt, password_hash FROM users'):
                    if not email or not salt or not hashed:
                        continue  # Device/demo identities are not commercial logins.
                    account_count += 1
                    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9._-]{0,35}', identity) or not re.fullmatch('[0-9a-f]{64}', salt) or not re.fullmatch('[0-9a-f]{64}', hashed):
                        invalid_accounts += 1
            return {'mode': 'read-only plan', 'consistentSnapshot': True, 'tableCounts': counts,
                    'passwordAccounts': account_count, 'accountsRequiringReview': invalid_accounts,
                    'cloudWrites': 0, 'readyForCutover': False,
                    'remaining': ['Migrate owner-scoped content, cases, evidence, history and integrations.',
                                  'Verify all private media and ownership before changing the Android endpoint.',
                                  'Freeze old-backend writes during a tested cutover; retain an encrypted backup.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(inventory(args.sqlite), indent=2))
    except (OSError, sqlite3.Error, ValueError):
        raise SystemExit('Inventory failed. Check the database path/schema; no records or credentials are printed.') from None
