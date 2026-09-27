from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config
import os

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    os.makedirs(os.path.join(app.static_folder, 'uploads'), exist_ok=True)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to continue.'

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app