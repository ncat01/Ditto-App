"""Create a consistent SQLite snapshot without overwriting an existing backup."""
from contextlib import closing
from pathlib import Path
import argparse
import sqlite3

def backup(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file(): raise ValueError('Source database does not exist')
    if source == destination or destination.exists(): raise ValueError('Choose a new backup filename')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            dst.commit()
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup failed integrity check')

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('destination'); a=p.parse_args()
    backup(a.source,a.destination); print('Consistent SQLite backup created. Back up private media separately.')
