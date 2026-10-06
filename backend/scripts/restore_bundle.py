"""Verify and restore a backup into a NEW empty directory. Never overwrite live data."""
from contextlib import closing
import argparse, hashlib, json, sqlite3, zipfile, shutil, tempfile
from pathlib import Path

def restore(bundle,destination,runtime_media_root=None):
    destination=Path(destination).resolve()
    if destination.exists():raise ValueError('Restore destination must not exist')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundle) as archive:
        if archive.getinfo('manifest.json').file_size>1024*1024:raise ValueError('Manifest too large')
        manifest=json.loads(archive.read('manifest.json'))
        if not isinstance(manifest,dict) or 'ditto.db' not in manifest:raise ValueError('Invalid manifest')
        with tempfile.TemporaryDirectory(dir=destination.parent) as directory:
            staging=Path(directory)
            for name,digest in manifest.items():
                target=(staging/name).resolve()
                if not target.is_relative_to(staging) or name=='manifest.json':raise ValueError('Invalid backup path')
                info=archive.getinfo(name)
                if info.file_size>1024*1024*1024:raise ValueError('Backup member too large')
                data=archive.read(name)
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Backup checksum mismatch')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            with closing(sqlite3.connect(staging/'ditto.db')) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid database')
                root=Path(runtime_media_root) if runtime_media_root else destination/'media'
                for identity,uri in db.execute('SELECT id,local_uri FROM content WHERE local_uri IS NOT NULL').fetchall():
                    original=Path(uri)
                    # Stored uploads use media/user-id/generated-filename; verify the archived counterpart.
                    relative=Path(original.parent.name)/original.name
                    if 'media/'+relative.as_posix() not in manifest:raise ValueError('Database references an unbacked original')
                    db.execute('UPDATE content SET local_uri=? WHERE id=?',(str(root/relative),identity))
                db.commit()
                if db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('Backup contains invalid references')
            shutil.move(str(staging),str(destination))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bundle');parser.add_argument('destination');parser.add_argument('--runtime-media-root');args=parser.parse_args()
    restore(args.bundle,args.destination,args.runtime_media_root)
    print('Checksums, database integrity and media references verified. Restore completed into new directory.')
