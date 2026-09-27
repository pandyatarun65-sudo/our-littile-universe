import os
from dotenv import load_dotenv

# Load variables from a .env file (if present) into the environment
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY is used by Flask to sign sessions/cookies. Keep it secret and
    # never commit the real value to Git — it lives in your .env file instead.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')

    # SQLite database file, stored inside the instance/ folder.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
