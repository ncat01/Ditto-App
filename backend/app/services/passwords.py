"""Argon2id passwords, with verification of existing PBKDF2 accounts for migration."""
import hashlib
import hmac
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

HASHER = PasswordHasher()
DUMMY = HASHER.hash('not-an-account-password')


def hash_password(password):
    return HASHER.hash(password)


def verify_password(password, encoded, salt=None):
    if encoded and encoded.startswith('$argon2id$'):
        try:
            return HASHER.verify(encoded, password)
        except (VerificationError, InvalidHashError):
            return False
    if encoded and salt:
        try:
            legacy = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 210000).hex()
            return hmac.compare_digest(encoded, legacy)
        except ValueError:
            return False
    try:
        HASHER.verify(DUMMY, password)
    except VerificationError:
        pass
    return False


def needs_upgrade(encoded):
    return not encoded.startswith('$argon2id$') or HASHER.check_needs_rehash(encoded)
