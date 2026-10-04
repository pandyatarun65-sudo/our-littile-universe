"""
Phase 7 security hardening. One place, called once from create_app():  init_security(app)

What it does (all server-side, no template changes needed):
  1. Private memory photos (/static/uploads/...) can only be opened when logged in.
  2. Same-origin check on every state-changing request (POST/PUT/PATCH/DELETE):
     protects the OLD forms (memories, letters) that have no csrf_token field.
  3. Security headers on every response.
  4. Friendly error pages (JSON for chat/notification calls) - no stack traces to the user.
  5. SQLite: foreign keys ON + busy timeout (fewer "database is locked" errors).
"""
import os
import sqlite3
from urllib.parse import urlparse

from flask import abort, jsonify, render_template, request, session
from sqlalchemy import event
from sqlalchemy.engine import Engine

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
    os.makedirs(app.config.get('DATA_DIR', app.instance_path), exist_ok=True)

    if app.config.get('IS_PRODUCTION'):
        # Render (and most hosts) sit behind a proxy: trust its forwarded host/scheme headers.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.before_request
    def _protect_requests():
        # 1) private photos: login required (the session cookie is signed, so this check is cheap and safe)
        if request.path.startswith(PRIVATE_PREFIX) and not session.get('_user_id'):
            abort(401)

        # 2) same-origin check for anything that changes data
        if request.method not in SAFE_METHODS:
            source = request.headers.get('Origin') or request.headers.get('Referer')
            if source and urlparse(source).netloc != request.host:
                abort(403)

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        # microphone is needed by our own chat page only; camera/location are never needed
        response.headers.setdefault('Permissions-Policy', 'microphone=(self), camera=(), geolocation=()')
        if request.path.startswith(PRIVATE_PREFIX):
            response.headers['Cache-Control'] = 'private, max-age=3600'
        elif request.method == 'GET' and response.mimetype == 'text/html':
            response.headers.setdefault('Cache-Control', 'no-store')   # private pages must not sit in shared caches
        return response

    @app.errorhandler(400)
    def _bad_request(_e):
        return _error(400, 'Something went wrong', 'That request could not be understood. Please go back and try again.')

    @app.errorhandler(401)
    def _unauthorized(_e):
        return _error(401, 'Please log in', 'You need to log in to see this.')

    @app.errorhandler(403)
    def _forbidden(_e):
        return _error(403, 'Not allowed', 'You do not have permission to do that.')

    @app.errorhandler(404)
    def _not_found(_e):
        return _error(404, 'Lost in space', 'We could not find what you were looking for.')

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
