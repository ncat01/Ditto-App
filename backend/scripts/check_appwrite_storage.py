"""Explicit opt-in live check: upload a generated image, inspect privacy, delete it."""
import argparse
import sys
import tempfile
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from app.providers.appwrite_storage import upload_private, delete_private
from app.providers.appwrite import AppwriteUnavailable

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Create and delete one temporary generated image in Appwrite.')
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
        return
    file_id = 'check' + uuid.uuid4().hex[:30]
    try:
        with tempfile.TemporaryDirectory(prefix='ditto-storage-check-') as folder:
            path = Path(folder) / 'connection-check.jpg'
            Image.new('RGB', (8, 8), '#ffc4cd').save(path, 'JPEG')
            try:
                upload_private(path, file_id)
                print('Private generated-image upload verified. No user content was uploaded.')
            finally:
                # Attempt cleanup even when the response was lost after a successful upload.
                delete_private(file_id)
                print('Temporary remote image removed (or confirmed absent).')
    except (AppwriteUnavailable, ValueError) as exc:
        print('Storage check failed: ' + str(exc))
        print('If cleanup failed, remove only the file with this ID in Console: ' + file_id)
        raise SystemExit(1) from None
    print('This verifies storage access only; it does not migrate SQLite or deploy Ditto.')

if __name__ == '__main__':
    main()
