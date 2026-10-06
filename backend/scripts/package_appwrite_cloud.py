"""Build a credential-free candidate Function archive, without deploying it."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ['app/__init__.py', 'app/config.py', 'app/matching/__init__.py',
         'app/matching/hasher.py', 'app/matching/video.py',
         'app/services/__init__.py', 'app/services/account_email.py',
         'app/api/__init__.py', 'app/api/account_pages.py', 'app/api/legal_pages.py',
         'app/providers/__init__.py', 'app/providers/instagram.py',
         'app/providers/web_search.py', 'app/providers/gemini.py']


def package(target):
    sources = [ROOT / item for item in ALLOW]
    sources += sorted((ROOT / 'cloud').glob('*.py'))
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, 'w:gz') as archive:
        for path in sources:
            archive.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
        archive.add(ROOT / 'cloud/requirements.txt', arcname='requirements.txt')
    return {'archive': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'files': len(sources) + 1, 'status': 'isolated candidate; not commercial-ready',
            'apiEntrypoint': 'cloud/main_api.py', 'workerEntrypoint': 'cloud/main_worker.py'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent / 'output/ditto-appwrite-candidate.tar.gz')
    args = parser.parse_args()
    print(json.dumps(package(args.output), indent=2))
