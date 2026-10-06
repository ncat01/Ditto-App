"""SQLite + referenced originals snapshot; credentials are deliberately excluded."""
from contextlib import closing
import argparse, hashlib, json, sqlite3, tempfile, zipfile
from pathlib import Path
from backup_sqlite import backup

def create(database, media, destination):
    database,media,destination=map(lambda p:Path(p).resolve(),(database,media,destination))
    if destination.exists():raise ValueError('Choose a new backup filename')
    destination.parent.mkdir(parents=True,exist_ok=True)
    staging=destination.with_suffix(destination.suffix+'.partial')
    try:
        with tempfile.TemporaryDirectory() as directory:
            snapshot=Path(directory)/'ditto.db';backup(database,snapshot)
            with closing(sqlite3.connect(snapshot)) as db:
                paths=[r[0] for r in db.execute('SELECT local_uri FROM content WHERE local_uri IS NOT NULL')]
            manifest={}
            with zipfile.ZipFile(staging,'x',zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot,'ditto.db')
                manifest['ditto.db']=hashlib.sha256(snapshot.read_bytes()).hexdigest()
                for original in paths:
                    source=Path(original).resolve()
                    relative=source.relative_to(media)
                    if not source.is_file():raise ValueError('A referenced original is missing; backup aborted')
                    name='media/'+relative.as_posix()
                    archive.write(source,name)
                    manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
                archive.writestr('manifest.json',json.dumps(manifest))
            staging.rename(destination)
    finally:
        staging.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('database');parser.add_argument('media');parser.add_argument('destination');args=parser.parse_args()
    create(args.database,args.media,args.destination)
    print('Database and referenced originals backed up. Keep the token encryption key in a separate secure backup.')
