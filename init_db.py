"""
Run this once to create the database tables and fill them with:
- your 2 user accounts (from .env)
- a few sample memories, so the timeline isn't empty on first login.

Usage:
    python init_db.py
"""

import os
from datetime import date
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User, Memory

load_dotenv()

app = create_app()

with app.app_context():
    # Create all tables defined in app/models.py
    db.create_all()

    # Only seed if there are no users yet, so re-running this script
    # doesn't create duplicates.
    if User.query.count() == 0:
        user1 = User(
            name=os.environ.get('USER1_NAME', 'Alex'),
            email=os.environ.get('USER1_EMAIL', 'alex@example.com').lower(),
            password_hash=generate_password_hash(
                os.environ.get('USER1_PASSWORD', 'changeme123')
            ),
        )
        user2 = User(
            name=os.environ.get('USER2_NAME', 'Sam'),
            email=os.environ.get('USER2_EMAIL', 'sam@example.com').lower(),
            password_hash=generate_password_hash(
                os.environ.get('USER2_PASSWORD', 'changeme456')
            ),
        )

        db.session.add_all([user1, user2])
        db.session.commit()

        print(f"Created users: {user1.email} and {user2.email}")

        sample_memories = [
            Memory(
                title="The day we met",
                description="Coffee, nerves, and way too much laughing for a first hello.",
                memory_date=date(2023, 4, 12),
                created_by=user1.id,
            ),
            Memory(
                title="First trip together",
                description="Got lost twice, didn't care once.",
                memory_date=date(2023, 8, 3),
                created_by=user2.id,
            ),
            Memory(
                title="A quiet Tuesday",
                description="Nothing special happened, and it was perfect anyway.",
                memory_date=date(2024, 2, 20),
                created_by=user1.id,
            ),
        ]

        db.session.add_all(sample_memories)
        db.session.commit()

        print(f"Added {len(sample_memories)} sample memories.")
    else:
        print("Users already exist — skipping seed data.")

    print("Database ready.")
