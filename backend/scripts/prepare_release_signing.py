"""Create an owner-held Android release key once; never print its passwords.

Keep .ditto-data/release-signing/ separately backed up. It is excluded from exports.
No APK is published and existing keys are never replaced.
"""
import argparse
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prepare(keytool, directory):
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    os.chmod(directory, 0o700)
    config = directory / 'signing.json'
    key = directory / 'ditto-release.jks'
    if config.exists() or key.exists():
        if not config.is_file() or not key.is_file():
            raise ValueError('Partial signing setup requires private review; never replace an existing key')
        return {'keyPrepared': True, 'existingKeyRetained': True, 'apkPublished': False}
    values = {'DITTO_SIGNING_STORE_FILE': str(key), 'DITTO_SIGNING_STORE_PASSWORD': secrets.token_urlsafe(32),
              'DITTO_SIGNING_KEY_ALIAS': 'ditto-production', 'DITTO_SIGNING_KEY_PASSWORD': secrets.token_urlsafe(32)}
    config.write_text(json.dumps(values), encoding='utf-8')
    os.chmod(config, 0o600)
    result = subprocess.run([str(keytool), '-genkeypair', '-noprompt', '-keystore', str(key),
        '-storetype', 'JKS', '-storepass:env', 'DITTO_SIGNING_STORE_PASSWORD', '-keypass:env', 'DITTO_SIGNING_KEY_PASSWORD',
        '-alias', values['DITTO_SIGNING_KEY_ALIAS'], '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000',
        '-dname', 'CN=Svarsha T'], env={**os.environ, **values}, capture_output=True, text=True)
    if result.returncode or not key.is_file():
        raise ValueError('Signing generation failed; review private files before retrying')
    os.chmod(key, 0o600)
    return {'keyPrepared': True, 'existingKeyRetained': False, 'apkPublished': False,
            'privateBackupRequired': 'Keep the release-signing directory in a separate secure backup before distributing a release.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keytool', type=Path)
    parser.add_argument('--create', action='store_true')
    args = parser.parse_args()
    if not args.create:
        print(json.dumps({'mode': 'plan', 'directory': '.ditto-data/release-signing', 'owner': 'Svarsha T', 'existingKeysReplaced': False}))
    else:
        try:
            executable = args.keytool or shutil.which('keytool') or Path(os.environ['JAVA_HOME']) / 'bin/keytool.exe'
            print(json.dumps(prepare(executable, ROOT / '.ditto-data/release-signing')))
        except Exception:
            raise SystemExit('Signing preparation stopped; no password or process output was printed. Existing keys are retained.') from None
