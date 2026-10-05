import sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from app.services.instagram_oauth import KEY_FILE
KEY_FILE.parent.mkdir(exist_ok=True)
if not KEY_FILE.exists():
    with KEY_FILE.open('x') as file:file.write(Fernet.generate_key().decode())
    os.chmod(KEY_FILE,0o600)
print('Token encryption storage initialized. Key stays private; back it up separately.')
