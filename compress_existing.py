"""One-time cleanup: shrink the raw images already stored in media_blobs.

Run on your LAPTOP, from the project root (next to run.py), with the Neon
DATABASE_URL in your local .env:

    python compress_existing.py

Originals are replaced by the compressed versions (max 1600px, quality 80).
"""
from app import create_app, db, storage
from app.models import MediaBlob

app = create_app()

with app.app_context():
    keys = [k for (k,) in db.session.query(MediaBlob.key).all()]
    print(f'{len(keys)} stored files found')
    saved_total = 0

    for key in keys:
        row = db.session.get(MediaBlob, key)
        old = bytes(row.data)
        new = storage._shrink_image(old, row.content_type, key)
        if len(new) < len(old):
            row.data = new
            db.session.commit()
            saved_total += len(old) - len(new)
            print(f'{key}: {len(old) // 1024} KB -> {len(new) // 1024} KB')
        db.session.expunge_all()          # keep memory low

    print(f'Done. Saved about {saved_total // (1024 * 1024)} MB.')
