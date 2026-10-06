"""Production housekeeping only; never runs synthetic outreach/follow-ups."""
import logging
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database.db import init_db
from app.services.account_deletion import purge_media

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
init_db()
while True:
    try:
        purge_media()
    except Exception:
        # Do not expose provider responses, credentials or customer file paths.
        logging.error('Media cleanup failed; pending jobs will be retried.')
    if '--once' in sys.argv:
        break
    time.sleep(30)
