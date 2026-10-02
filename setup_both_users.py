from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    print("[+] Re-creating database schema...")
    db.drop_all()
    db.create_all()

    # Yahan apne custom password set kar sakte ho
    user1 = User(
        username="tarun",
        email="pandyatarun65@gmail.com",
        name="Tarun",
        password_hash=generate_password_hash("@kuku_77")
    )
    user2 = User(
        username="kuku",
        email="hemlatasharma626751@gmail.com",
        name="Kuku",
        password_hash=generate_password_hash("radhe_radhe")
    )

    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
    print("[✓] Database ready with Tarun and Kuku accounts created!")