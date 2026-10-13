"""
Phase 7 security hardening. One place, called once from create_app():  init_security(app)

  1. Private memory photos: served by a login-protected route from UPLOAD_DIR
     (and, for old photos, from app/static/uploads). The URL stays /static/uploads/<name>,
     so no template needed to change.
  2. CSRF: every POST/PUT/PATCH/DELETE must carry the session's csrf token
     (form field `csrf_token` or header `X-CSRF-Token`), plus a same-origin check.
  3. Security headers on every response.
  4. Friendly error pages (JSON for chat/notification calls) - no stack traces to the user.
  5. SQLite: foreign keys ON + busy timeout.
  6. /healthz for the hosting platform's health check (no data, no login).
"""
import logging
import os
import sqlite3
from urllib.parse import urlparse

from flask import abort, jsonify, render_template, request, session
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app import storage
from app.security import check_csrf
from app.utils import PHOTO_MIME, PHOTO_NAME_RE


SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
PRIVATE_PREFIX = '/static/uploads/'
JSON_PREFIXES = ('/chat/', '/notifications/summary')


@event.listens_for(Engine, 'connect')
def _sqlite_pragmas(dbapi_connection, _record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=10000')
        cursor.close()


def _wants_json():
    return request.path.startswith(JSON_PREFIXES) or request.accept_mimetypes.best == 'application/json'


def _error(code, title, message):
    if _wants_json():
        return jsonify(error=message), code
    try:
        return render_template('error.html', code=code, title=title, message=message), code
    except Exception:                       # never let the error page itself crash
        return f'{code} - {title}', code


def init_security(app):
    data_dir = app.config.get('DATA_DIR') or app.instance_path
    upload_dir = app.config.get('UPLOAD_DIR') or os.path.join(data_dir, 'uploads')
    app.config.setdefault('UPLOAD_DIR', upload_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    if app.config.get('IS_PRODUCTION'):
        # Render sits behind a proxy: trust its forwarded host/scheme/ip headers (real client IP for rate limiting).
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
        app.logger.setLevel(logging.INFO)

    @app.before_request
    def _protect_requests():
        # 1) private photos: login required (the session cookie is signed, so this is cheap and safe)
        if request.path.startswith(PRIVATE_PREFIX) and not session.get('_user_id'):
            abort(401)

        if request.method not in SAFE_METHODS:
            # 2a) same-origin check
            source = request.headers.get('Origin') or request.headers.get('Referer')
            if source and urlparse(source).netloc != request.host:
                abort(403)
            # 2b) CSRF token for EVERY state-changing request (forms and fetch calls)
            check_csrf()

    # ---- private photo route: more specific than Flask's built-in /static/<path>, so it wins
    @app.route(PRIVATE_PREFIX + '<path:filename>')
    def private_upload(filename):
        if not session.get('_user_id'):
            abort(401)
        name = os.path.basename(filename)
        if not PHOTO_NAME_RE.match(name):
            abort(404)
        response = storage.send(f'uploads/{name}', PHOTO_MIME.get(name.rsplit('.', 1)[1]))
        if response is None:
            abort(404)
        return response

    @app.route('/healthz')
    def healthz():
        return 'ok', 200, {'Content-Type': 'text/plain', 'Cache-Control': 'no-store'}

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        response.headers.setdefault('Permissions-Policy', 'microphone=(self), camera=(), geolocation=()')
        if request.path.startswith(PRIVATE_PREFIX):
            response.headers['Cache-Control'] = 'private, max-age=3600'
        elif request.method == 'GET' and response.mimetype == 'text/html':
            response.headers.setdefault('Cache-Control', 'no-store')
        return response

    @app.errorhandler(400)
    def _bad_request(_e):
        return _error(400, 'Something went wrong', 'That request could not be verified. Please go back, refresh the page and try again.')

    @app.errorhandler(401)
    def _unauthorized(_e):
        return _error(401, 'Please log in', 'You need to log in to see this.')

    @app.errorhandler(403)
    def _forbidden(_e):
        return _error(403, 'Not allowed', 'You do not have permission to do that.')

    @app.errorhandler(404)
    def _not_found(_e):
        return _error(404, 'Lost in space', 'We could not find what you were looking for.')

    @app.errorhandler(405)
    def _method_not_allowed(_e):
        return _error(405, 'Not allowed', 'That action is not available this way.')

    @app.errorhandler(413)
    def _too_large(_e):
        return _error(413, 'File too large', 'That file is too large (max 5 MB).')

    @app.errorhandler(500)
    def _server_error(_e):
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
        return _error(500, 'Something broke', 'Something went wrong on our side. Nothing was lost - please try again.')
