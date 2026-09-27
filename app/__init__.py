from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# These are created here (empty) and "attached" to the app inside create_app().
# This pattern is called the "application factory" pattern.
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    # If a page requires login and the user isn't logged in, Flask-Login
    # will redirect them to this route.
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to continue.'

    # Import blueprints here (not at the top of the file) to avoid
    # circular-import problems, since routes.py files import `db` from here.
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
