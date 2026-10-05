"""Small cross-platform supervisor; data lives in the repository workspace.

Run from repository root: .venv/bin/python backend/scripts/codespaces.py start
Only one API and one scheduler run. No shell interpolation or secret output.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / '.ditto-data'
BACKEND = ROOT / 'backend'

def environment():
    env = os.environ.copy()
    env.update(DITTO_DATABASE_URL='sqlite:///' + (DATA / 'ditto.db').as_posix(),
               DITTO_MEDIA_ROOT=str(DATA / 'media'), DITTO_DEMO_MODE='true')
    if env.get('CODESPACE_NAME'):env.setdefault('PUBLIC_BASE_URL', 'https://' + env['CODESPACE_NAME'] + '-8010.app.github.dev')
    env['PYTHONPATH'] = str(BACKEND)
    return env

def healthy():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8010/api/health', timeout=2) as r:
            return json.load(r).get('database') == 'connected'
    except Exception:
        return False

def run():
    DATA.mkdir(exist_ok=True)
    env = environment()
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=BACKEND, env=env, check=True)
    commands = [[sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8010', '--workers', '1', '--no-access-log'],
                [sys.executable, 'scripts/scheduler.py']]
    children = [subprocess.Popen(c, cwd=BACKEND, env=env) for c in commands]
    def stop(*_):
        for p in children:
            if p.poll() is None: p.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while all(p.poll() is None for p in children): time.sleep(1)
    finally:
        stop()
        for p in children:
            try: p.wait(timeout=10)
            except subprocess.TimeoutExpired: p.kill(); p.wait()

def start():
    if healthy():
        print('Ditto API is already running on port 8010.'); return
    DATA.mkdir(exist_ok=True)
    with (DATA / 'backend.log').open('ab') as log:
        options = {'start_new_session': True} if os.name != 'nt' else {'creationflags': subprocess.CREATE_NO_WINDOW}
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'run'], cwd=ROOT,
                         stdout=log, stderr=log, **options)
    for _ in range(60):
        if healthy():
            name = os.environ.get('CODESPACE_NAME')
            print('Ditto backend ready. ' + (f'Forwarded URL: https://{name}-8010.app.github.dev/' if name else 'http://127.0.0.1:8010/'))
            print('Port remains private by default. For the phone, use the documented public test port with Ditto authentication.')
            return
        time.sleep(1)
    raise SystemExit('Startup failed. Inspect .ditto-data/backend.log (do not share secrets).')

if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='run': run()
    else: start()
