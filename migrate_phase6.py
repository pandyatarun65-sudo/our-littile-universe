"""
PHASE 6 — ONE-TIME DATABASE MIGRATION

Run this once, after models.py has been updated with the Phase 6 changes
(ChatMessage, Notification, User.last_seen).

What this does:
1. Adds a `last_seen` column to the existing `users` table (safe — SQLite
   supports simple ADD COLUMN; nothing is dropped or renamed).
2. Creates two brand-new tables: `chat_messages` and `notifications`.

What this does NOT do:
- It never touches `user`, `memory`, `photo` (the old backup tables).
- It never touches existing rows in `users`, `memories`, `photos`,
  `secret_letters`, `special_dates`, `daily_answers`.
- It's safe to run more than once — every step checks first and skips
  itself if already done.

Usage:
    python migrate_phase6.py
"""

import sqlite3

from app import create_app, db

app = create_app()

with app.app_context():
    db_path = db.engine.url.database
    print(f'Using database: {db_path}')

    raw = sqlite3.connect(db_path)
    cur = raw.cursor()

    # ---------- Step 1: add users.last_seen if it isn't already there ----------
    existing_columns = {row[1] for row in cur.execute('PRAGMA table_info(users)').fetchall()}
    if 'last_seen' in existing_columns:
        print('users.last_seen already exists — skipping.')
    else:
        cur.execute('ALTER TABLE users ADD COLUMN last_seen DATETIME')
        raw.commit()
        print('Added users.last_seen')

    raw.close()

    # ---------- Step 2: create chat_messages + notifications ----------
    # db.create_all() only creates tables that don't exist yet — it never
    # touches or drops anything that's already there.
    before = set(db.inspect(db.engine).get_table_names())
    db.create_all()
    after = set(db.inspect(db.engine).get_table_names())
    created = after - before

    if created:
        print(f'Created new table(s): {", ".join(sorted(created))}')
    else:
        print('chat_messages and notifications already exist — skipping.')

    print()
    print('Migration complete. Existing data was not touched.')