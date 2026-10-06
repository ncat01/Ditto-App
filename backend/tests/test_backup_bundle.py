import importlib.util, sqlite3, sys, json, zipfile
from pathlib import Path
import pytest
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
from backup_bundle import create
from restore_bundle import restore

def test_snapshot_restore_and_no_overwrite(tmp_path):
    media=tmp_path/'media';original=media/('a'*32)/'video.mp4';original.parent.mkdir(parents=True);original.write_bytes(b'original')
    database=tmp_path/'source.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE content (id TEXT, local_uri TEXT)')
        db.execute('INSERT INTO content VALUES (?,?)',('one',str(original)));db.commit()
    bundle=tmp_path/'snapshot.zip';create(database,media,bundle)
    target=tmp_path/'restored';restore(bundle,target)
    assert (target/'media'/('a'*32)/'video.mp4').read_bytes()==b'original'
    with sqlite3.connect(target/'ditto.db') as db:
        assert Path(db.execute('SELECT local_uri FROM content').fetchone()[0]).is_file()
    with pytest.raises(ValueError):restore(bundle,target)
    with pytest.raises(ValueError):create(database,media,bundle)

def test_corruption_and_traversal_are_rejected(tmp_path):
    import hashlib
    for name,data,digest in [('ditto.db',b'wrong','invalid'),('../outside',b'evil',hashlib.sha256(b'evil').hexdigest())]:
        bundle=tmp_path/(str(len(name))+'.zip')
        with zipfile.ZipFile(bundle,'w') as archive:
            archive.writestr(name,data);archive.writestr('manifest.json',json.dumps({name:digest,'ditto.db':digest}))
        with pytest.raises((ValueError,KeyError)):restore(bundle,tmp_path/(str(len(name))+'-restore'))
    assert not (tmp_path/'outside').exists()
