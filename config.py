import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

# APP_ENV=production Render par set hona chahiye. Laptop par mat set karo.
APP_ENV = os.environ.get('APP_ENV', 'development').strip().lower()
IS_PRODUCTION = APP_ENV == 'production'
ON_RENDER = bool(os.environ.get('RENDER'))   # Render hamesha RENDER=true set karta hai

_WEAK_KEYS = {'', 'dev-key-change-me', 'change-me', 'secret', 'secret-key', 'changeme'}


def _load_secret_key():
    key = os.environ.get('SECRET_KEY', '').strip()
    if IS_PRODUCTION and (key in _WEAK_KEYS or len(key) < 32):
        raise RuntimeError(
            'SECRET_KEY is missing or too weak. In production set a random value of 32+ characters '
            '(python -c "import secrets; print(secrets.token_hex(32))").')
    return key or 'dev-key-change-me'      # sirf local development ke liye


def _database_uri(data_dir):
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        if url.startswith('postgres://'):            # purana scheme; SQLAlchemy ko postgresql:// chahiye
            url = 'postgresql://' + url[len('postgres://'):]
        return url
    if IS_PRODUCTION or ON_RENDER:
        # Server par SQLite par kabhi fallback nahi: wo file restart par mit jaati hai.
        raise RuntimeError('DATABASE_URL is not set. Add your Neon connection string in Render > Environment.')
    return 'sqlite:///' + os.path.join(data_dir, 'database.db')


class Config:
    SECRET_KEY = _load_secret_key()

    # Laptop par: instance folder (SQLite + local uploads). Render par DB Neon me hai
    # aur media object storage me, ye folder sirf temporary hai.
    DATA_DIR = os.path.abspath(os.environ.get('DATA_DIR') or os.path.join(basedir, 'instance'))
    _DB_URI = _database_uri(DATA_DIR)
    SQLALCHEMY_DATABASE_URI = _DB_URI
    SQLALCHEMY_ENGINE_OPTIONS = {} if _DB_URI.startswith('sqlite') else {
        'pool_pre_ping': True,                    # Neon idle par suspend hota hai
        'pool_recycle': 300,
        'connect_args': {'connect_timeout': 15},  # Neon ko jaagne ka time
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_DIR = os.path.abspath(os.environ.get('UPLOAD_DIR') or os.path.join(DATA_DIR, 'uploads'))

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    DEBUG = False
    TESTING = False

    # Session cookie hardening
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 14   # 14 days

    IS_PRODUCTION = IS_PRODUCTION
    ON_RENDER = ON_RENDER