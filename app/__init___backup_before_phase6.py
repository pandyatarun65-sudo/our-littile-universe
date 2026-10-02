import os
from datetime import datetime, date
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from markupsafe import Markup, escape
from dotenv import load_dotenv


load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=None):
    app = Flask(__name__)

    if config_class is None:
        from config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    os.makedirs(app.config.get('UPLOAD_FOLDER', 'app/static/uploads'), exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to enter our universe.'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.surprises.routes import surprises_bp
    from app.smart.routes import smart_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(surprises_bp)
    app.register_blueprint(smart_bp)

    # Robust date formatter supporting strings, datetime, and date objects
    @app.template_filter('date_format')
    def date_format(value, format='%B %d, %Y'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return value
        return value.strftime(format)

    # Custom nl2br filter so letter linebreaks render safely without crashing
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if not s:
            return ''
        return Markup('<br>\n'.join(escape(s).split('\n')))

    return app