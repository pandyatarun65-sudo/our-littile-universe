"""
ONE-TIME REPAIR SCRIPT — run this once, then delete it.

What went wrong (in plain terms):
1. When Phase 4 renamed the database tables (user -> users, memory -> memories,
   photo -> photos), your OLD real data (2 accounts, 3 memories, 3 photos)
   stayed behind in the OLD tables. The app now only reads the NEW tables,
   which were empty except for some placeholder/test accounts.
2. One of those placeholder accounts ended up with the wrong email
   (kuku@universe.com instead of your partner's real email), and neither
   account's password matched what is currently in your .env file.
3. Your one "Open When" letter got linked to the placeholder accounts
   instead of your real two accounts.

This script:
- Resets both real accounts' passwords to match your CURRENT .env file
- Fixes your partner's email to match .env
- Re-links your existing letter to the correct real accounts
- Copies your 3 old memories + their 3 photos into the new tables
- Removes the leftover placeholder accounts
- Leaves the old tables untouched, as a backup (nothing is deleted from them)

Usage:
    python fix_data_mismatch.py
"""

import os
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User, Memory, Photo, SecretLetter

load_dotenv()

app = create_app()

with app.app_context():
    db_path = os.path.join(app.instance_path, 'database.db')
    raw = sqlite3.connect(db_path)
    raw_cur = raw.cursor()

    # ---------- Step 1: fix the two real accounts ----------
    user1_email = os.environ['USER1_EMAIL'].strip().lower()
    user2_email = os.environ['USER2_EMAIL'].strip().lower()

    user1 = User.query.filter_by(email=user1_email).first()
    if not user1:
        raise SystemExit(f'Could not find a users row with email {user1_email}. Stopping to avoid guessing wrong.')
    user1.password_hash = generate_password_hash(os.environ['USER1_PASSWORD'])
    user1.name = os.environ.get('USER1_NAME', user1.name)
    print(f'Fixed password for {user1.email} (id={user1.id})')

    # Your partner's account currently has the WRONG email — find it by name
    # instead, since email can't be trusted yet.
    user2 = User.query.filter(User.email != user1_email, User.id != user1.id).filter(
        db.or_(User.username == 'kuku', User.email == 'kuku@universe.com')
    ).first()
    if not user2:
        raise SystemExit('Could not find your partner\'s placeholder account (kuku). Stopping — check manually.')

    old_user2_id = user2.id
    user2.email = user2_email
    user2.username = user2_email
    user2.name = os.environ.get('USER2_NAME', user2.name)
    user2.password_hash = generate_password_hash(os.environ['USER2_PASSWORD'])
    print(f'Fixed email + password for {user2.email} (id={user2.id})')

    db.session.commit()

    # ---------- Step 2: re-link the existing letter(s) to the real accounts ----------
    # Any letter pointing at the junk placeholder ids (1 or 2, the "user1"/"user2"
    # test accounts) gets redirected to the real accounts instead.
    junk_ids = {row[0] for row in raw_cur.execute(
        "SELECT id FROM users WHERE username IN ('user1', 'user2')"
    ).fetchall()}

    letters = SecretLetter.query.all()
    for letter in letters:
        if letter.user_id in junk_ids:
            letter.user_id = user1.id
        if letter.recipient_id in junk_ids:
            letter.recipient_id = old_user2_id if old_user2_id not in junk_ids else user2.id
    db.session.commit()
    print(f'Checked {len(letters)} letter(s) for junk account links.')

    # ---------- Step 3: migrate old memories + photos into the new tables ----------
    # Map: old 'user' table id 1 -> user1 (Tarun), old id 2 -> user2 (partner)
    old_id_map = {1: user1.id, 2: user2.id}

    old_memories = raw_cur.execute(
        'SELECT id, title, description, memory_date, created_by, created_at FROM memory'
    ).fetchall()

    migrated = 0
    for old_id, title, description, memory_date, created_by, created_at in old_memories:
        new_creator_id = old_id_map.get(created_by, user1.id)

        new_memory = Memory(
            title=title,
            description=description,
            memory_date=datetime.strptime(memory_date, '%Y-%m-%d').date(),
            created_by=new_creator_id,
        )
        db.session.add(new_memory)
        db.session.flush()  # gets new_memory.id without a full commit yet

        for photo_id, file_path, caption, uploaded_at in raw_cur.execute(
            'SELECT id, file_path, caption, uploaded_at FROM photo WHERE memory_id = ?', (old_id,)
        ).fetchall():
            db.session.add(Photo(
                memory_id=new_memory.id,
                file_path=file_path,
                caption=caption,
                uploaded_by=new_creator_id,
            ))
        migrated += 1

    db.session.commit()
    print(f'Migrated {migrated} old memory(ies) and their photos into the new tables.')

    # ---------- Step 4: remove the leftover placeholder accounts ----------
    deleted = User.query.filter(User.username.in_(['user1', 'user2'])).delete(synchronize_session=False)
    db.session.commit()
    print(f'Removed {deleted} placeholder account(s).')

    # ---------- Summary ----------
    print()
    print('Done. Final state:')
    print(' users:', User.query.count())
    print(' memories:', Memory.query.count())
    print(' photos:', Photo.query.count())
    print(' letters:', SecretLetter.query.count())
    for u in User.query.all():
        print('  -', u.id, u.email, u.name)

    raw.close()