"""
Non-destructive database migration script for Phase 4.
Creates the `secret_letters` table inside instance/database.db without touching existing memories.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')


def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}. Please run 'python init_db.py' first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='secret_letters';")
    exists = cursor.fetchone()

    if exists:
        print("[✓] Table 'secret_letters' already exists. Nothing to do.")
    else:
        print("[+] Creating 'secret_letters' table...")
        cursor.execute('''
            CREATE TABLE secret_letters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category VARCHAR(30) NOT NULL DEFAULT 'letter',
                title VARCHAR(200) NOT NULL,
                body TEXT NOT NULL,
                unlock_date DATE NULL,
                cover_hint VARCHAR(255) NULL,
                mood_tag VARCHAR(50) NULL,
                box_type VARCHAR(50) NULL DEFAULT 'gift',
                user_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(recipient_id) REFERENCES users(id)
            );
        ''')
        conn.commit()
        print("[✓] Phase 4 table 'secret_letters' successfully created!")

    conn.close()


if __name__ == '__main__':
    run_migration()