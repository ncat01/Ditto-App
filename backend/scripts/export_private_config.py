"""Export allowlisted runner configuration encrypted for the same deployment key.

For a private Codespaces-to-owner-workstation transfer. Never attach the file
to chat, commit it or publish it. No secret values are printed.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('INSTAGRAM_APP_SECRET', 'TOKEN_ENCRYPTION_KEY', 'GEMINI_API_KEY',
         'GOOGLE_CLOUD_API_KEY', 'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER',
         'SMTP_PASSWORD', 'SMTP_FROM', 'INSTAGRAM_APP_ID', 'VISION_MONTHLY_UNIT_LIMIT')


def transfer_cipher(key):
    if not key or len(key) < 30:
        raise ValueError('Complete deployment key required')
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(
        b'ditto-private-config-transfer-v1\x00' + key.encode()).digest()))


def main():
    values = {name: os.environ[name] for name in NAMES if os.getenv(name)}
    old_key = ROOT / '.ditto-data/token-encryption.key'
    if not values.get('TOKEN_ENCRYPTION_KEY') and old_key.is_file():
        values['TOKEN_ENCRYPTION_KEY'] = old_key.read_text(encoding='utf-8').strip()
    if not values.get('TOKEN_ENCRYPTION_KEY') or not values.get('INSTAGRAM_APP_SECRET'):
        raise ValueError('Original encryption key and Instagram app secret must be available')
    Fernet(values['TOKEN_ENCRYPTION_KEY'].encode())
    target = ROOT / '.ditto-data/ditto-private-config.enc'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(transfer_cipher(os.environ['APPWRITE_DEPLOY_KEY']).encrypt(
        json.dumps(values).encode()))
    os.chmod(target, 0o600)
    print('Encrypted configuration saved: .ditto-data/ditto-private-config.enc')
    print('Download privately to your workstation. Do not attach to chat or commit it.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit('Export stopped. Original private configuration and the same deployment key are required. No secret was printed.') from None
