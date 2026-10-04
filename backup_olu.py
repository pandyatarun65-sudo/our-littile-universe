"""
Backup for Our Little Universe.  Run from the project root:

    python backup_olu.py

Creates  backups/olu_backup_YYYYMMDD_HHMMSS.zip  containing:
  - the SQLite database (copied with SQLite's own backup API, so it is consistent even while the app runs)
  - app/static/uploads/   (memory photos)
  - <DATA_DIR>/chat_media/ (private chat photos + voice notes)
It keeps the newest 10 backups and deletes older ones.

NOT included on purpose: .env (secrets). Keep those in a password manager.
The backups/ folder is in .gitignore - NEVER upload it to GitHub (it holds your private data).
"""
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
BASE = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.abspath(os.environ.get('DATA_DIR') or os.path.join(BASE, 'instance'))
DB_FILE = os.path.join(DATA_DIR, 'database.db')
UPLOADS = os.path.join(BASE, 'app', 'static', 'uploads')
CHAT_MEDIA = os.path.join(DATA_DIR, 'chat_media')
OUT_DIR = os.path.join(BASE, 'backups')
KEEP = 10


def add_folder(archive, folder, arc_root):
    count = 0
    if os.path.isdir(folder):
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if name == '.gitkeep':
                    continue
                full = os.path.join(root, name)
                archive.write(full, os.path.join(arc_root, os.path.relpath(full, folder)))
                count += 1
    return count


def main():
    if not os.path.isfile(DB_FILE):
        raise SystemExit(f'Database not found: {DB_FILE}')
    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    target = os.path.join(OUT_DIR, f'olu_backup_{stamp}.zip')

    with tempfile.TemporaryDirectory() as tmp:
        snapshot = os.path.join(tmp, 'database.db')
        source = sqlite3.connect(DB_FILE)
        copy = sqlite3.connect(snapshot)
        with copy:
            source.backup(copy)
        source.close()
        copy.close()

        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, 'database.db')
            photos = add_folder(archive, UPLOADS, 'uploads')
            media = add_folder(archive, CHAT_MEDIA, 'chat_media')

    print(f'Backup saved: {target}')
    print(f'  database.db + {photos} memory photo(s) + {media} chat media file(s)')

    old = sorted(f for f in os.listdir(OUT_DIR) if f.startswith('olu_backup_') and f.endswith('.zip'))
    for name in old[:-KEEP]:
        os.remove(os.path.join(OUT_DIR, name))
        print(f'  removed old backup {name}')


if __name__ == '__main__':
    main()
