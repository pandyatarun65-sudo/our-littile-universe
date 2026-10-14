import os
import traceback
from app import create_app, db

app = create_app()

with app.app_context():
    try:
        db.create_all()
        import setup_both_users
    except Exception:
        traceback.print_exc()      # Render Logs me poora error dikhega

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
