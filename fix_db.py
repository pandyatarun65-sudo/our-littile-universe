import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'database.db')

def fix_database():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database file not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. users table mein email column check aur add karna
    cursor.execute("PRAGMA table_info(users);")
    columns = [col[1] for col in cursor.fetchall()]

    if 'email' not in columns:
        print("[+] Adding 'email' column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(120);")
        # Existing users ke email ko username ke barabar set karna
        cursor.execute("UPDATE users SET email = username WHERE email IS NULL;")
        conn.commit()
        print("[✓] 'email' column added successfully.")
    else:
        print("[✓] 'email' column already exists in users table.")

    # 2. secret_letters table check aur add karna (Phase 4)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='secret_letters';")
    if not cursor.fetchone():
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
        print("[✓] 'secret_letters' table ready.")
    else:
        print("[✓] 'secret_letters' table already exists.")

    conn.close()
    print("\n[✓] Database completely fixed and synced!")

if __name__ == '__main__':
    fix_database()