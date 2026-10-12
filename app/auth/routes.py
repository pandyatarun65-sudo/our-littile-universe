from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app.models import User
from app.ratelimit import login_locked_seconds, record_login_failure, clear_login_failures

auth_bp = Blueprint('auth', __name__)

# Used when the e-mail does not exist, so "unknown e-mail" and "wrong password"
# take the same time (an attacker cannot tell which e-mails are real).
_DUMMY_HASH = generate_password_hash('not-a-real-password')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If someone is already logged in, skip the login page.
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        ip = request.remote_addr or 'unknown'

        # Phase 7: too many wrong attempts from this address -> wait.
        wait = login_locked_seconds(ip)
        if wait:
            minutes = max(1, round(wait / 60))
            flash(f'Too many attempts. Please wait about {minutes} minute(s) and try again.')
            return render_template('login.html'), 429

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        # check_password_hash compares the typed password against the
        # stored hash — the real password is never saved anywhere.
        password_ok = (
            len(password) <= 1000
            and check_password_hash(user.password_hash if user else _DUMMY_HASH, password)
        )

        if user and password_ok:
            clear_login_failures(ip)
            session.clear()              # start a fresh session for the logged-in user
            login_user(user)
            return redirect(url_for('main.dashboard'))

        record_login_failure(ip)
        flash('Incorrect email or password.')

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])      # Phase 7: POST only (the CSRF token is checked globally)
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
