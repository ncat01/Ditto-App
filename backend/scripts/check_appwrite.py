"""Read-only credential check; does not print keys or database contents."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers.appwrite import check_connection, AppwriteUnavailable

try:
    check_connection()
except AppwriteUnavailable as exc:
    raise SystemExit('Appwrite check failed: ' + str(exc))
print('Appwrite connected: project and database-list access verified.')
print('No databases, files or accounts were changed. SQLite remains the active database.')
