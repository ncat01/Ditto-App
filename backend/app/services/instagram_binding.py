"""Operator binding of a deployment's test Instagram token to one Ditto user."""
import hashlib,json
from pathlib import Path
from app.config import get_settings

BINDING_FILE=Path(__file__).resolve().parents[3]/'.ditto-data/instagram-owner.json'

def token_digest():
    token=get_settings().meta_access_token.get_secret_value()
    return hashlib.sha256(token.encode()).hexdigest() if token else ''

def owner_binding(user_id):
    try:
        binding=json.loads(BINDING_FILE.read_text())
        if binding['ditto_user_id']==user_id and binding['token_digest']==token_digest() and token_digest():
            return binding
    except (OSError,ValueError,KeyError,TypeError):pass
    return None
