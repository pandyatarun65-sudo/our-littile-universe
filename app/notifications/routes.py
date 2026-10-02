"""Notification routes. Every route needs login and only touches the user's OWN notifications."""
from flask import Blueprint, abort, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Notification
from app.security import check_csrf
from app.chat.services import touch_presence, mark_delivered, iso_utc
from app.notifications.services import (
    ensure_generated_notifications, notification_url, unread_count, unread_chat_count,
)

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.app_context_processor
def inject_notification_counts():
    """Gives every page the unread numbers for the bell + chat dot (first paint)."""
    try:
        if current_user.is_authenticated:
            return {
                'unread_notification_count': unread_count(current_user.id),
                'chat_unread': unread_chat_count(current_user.id) > 0,
            }
    except Exception:            # e.g. Phase 6 tables missing: never break normal pages
        db.session.rollback()
    return {'unread_notification_count': 0, 'chat_unread': False}


def _own_notification_or_404(notification_id):
    note = db.session.get(Notification, notification_id)
    if note is None or note.recipient_id != current_user.id:
        abort(404)                       # someone else's: same answer as "missing"
    return note


@notifications_bp.route('/notifications')
@login_required
def notifications_page():
    ensure_generated_notifications(current_user.id)
    items = (Notification.query.filter_by(recipient_id=current_user.id)
             .order_by(Notification.created_at.desc()).limit(60).all())
    return render_template('notifications.html', items=items, iso_utc=iso_utc)


@notifications_bp.route('/notifications/summary')
@login_required
def notifications_summary():
    """Called every ~30 s by notifications.js on every page. Also counts as 'app is open' for presence."""
    ensure_generated_notifications(current_user.id)
    touch_presence(current_user.id)
    mark_delivered(current_user.id)
    return jsonify(unread=unread_count(current_user.id),
                   chat_unread=unread_chat_count(current_user.id) > 0)


@notifications_bp.route('/notifications/<int:notification_id>/go')
@login_required
def notification_go(notification_id):
    note = _own_notification_or_404(notification_id)
    if not note.is_read:
        note.mark_read()
        db.session.commit()
    return redirect(notification_url(note))


@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def notification_read(notification_id):
    check_csrf()
    note = _own_notification_or_404(notification_id)
    if not note.is_read:
        note.mark_read()
        db.session.commit()
    return redirect(url_for('notifications.notifications_page'))


@notifications_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def notifications_read_all():
    check_csrf()
    for note in Notification.query.filter_by(recipient_id=current_user.id, is_read=False).all():
        note.mark_read()
    db.session.commit()
    return redirect(url_for('notifications.notifications_page'))
