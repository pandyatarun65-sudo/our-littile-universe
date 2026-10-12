import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

# APP_ENV=production must be set on the server (Render). On your laptop leave it unset.
APP_ENV = os.environ.get('APP_ENV', 'development').strip().lower()
IS_PRODUCTION = APP_ENV == 'production'

_WEAK_KEYS = {'', 'dev-key-change-me', 'change-me', 'secret', 'secret-key', 'changeme'}


def _load_secret_key():
    key = os.environ.get('SECRET_KEY', '').strip()
    if IS_PRODUCTION and (key in _WEAK_KEYS or len(key) < 32):
        # Fail loudly instead of silently running with a guessable key.
        raise RuntimeError(
            'SECRET_KEY is missing or too weak. In production set a random value of 32+ characters '
            '(python -c "import secrets; print(secrets.token_hex(32))").')
    return key or 'dev-key-change-me'      # local development only


class Config:
    SECRET_KEY = _load_secret_key()

    # DATA_DIR = ONE folder that holds everything private and must survive restarts:
    # the database, memory photos (uploads/) and chat media (chat_media/).
    # Laptop: defaults to the "instance" folder.  Render: set DATA_DIR=/var/data (the persistent disk).
    DATA_DIR = os.path.abspath(os.environ.get('DATA_DIR') or os.path.join(basedir, 'instance'))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATA_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.path.abspath(os.environ.get('UPLOAD_DIR') or os.path.join(DATA_DIR, 'uploads'))

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    DEBUG = False
    TESTING = False

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = IS_PRODUCTION        # cookie only over https on the server
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14   # 14 days

    IS_PRODUCTION = IS_PRODUCTION
