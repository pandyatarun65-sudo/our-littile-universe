import os
from app import create_app, db

app = create_app()

# Auto-initialize database tables and initial users on startup
with app.app_context():
    try:
        db.create_all()
        # Initial users create karne ke liye
        import setup_both_users
    except Exception as e:
        print(f"Startup DB init notice: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)