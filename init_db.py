"""
Database initialization script for Our Little Universe.
Creates tables and default users using display_name.
"""
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("[+] Creating all database tables...")
    db.create_all()

    # Check if any user already exists
    if not User.query.first():
        print("[+] Creating default universe users...")
        user1 = User(
            username='user1',
            display_name='Partner 1',
            password_hash=generate_password_hash('password123')
        )
        user2 = User(
            username='user2',
            display_name='Partner 2',
            password_hash=generate_password_hash('password123')
        )
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        print("[✓] Default users created: 'user1' and 'user2' (Password: password123)")
    else:
        print("[✓] Users already exist in database.")

    print("[✓] Database initialization complete!")