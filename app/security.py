"""
Tiny CSRF protection shared by Phase 5 (smart) and Phase 6 (chat, notifications).
A random token lives in the session; forms send it as `csrf_token`,
JavaScript (fetch) sends it in the `X-CSRF-Token` header.
"""
import hmac
import secrets

from flask import abort, request, session


def get_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']


def check_csrf():
    sent = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
    real = session.get('csrf_token', '')
    if not real or not sent or not hmac.compare_digest(sent.encode(), real.encode()):
        abort(400)
