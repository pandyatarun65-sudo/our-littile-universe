"""
Notification helpers (work with the Notification model in app/models.py).
Notifications are created by the SERVER only and belong to exactly one user (recipient_id).
"""
import json
import re
from datetime import datetime, timezone, timedelta, date

from flask import url_for

from app import db
from app.models import Notification, SecretLetter, SpecialDate, User

# Only these pages can be opened from a notification (the link is built on the server).
ALLOWED_LINKS = {
    'chat.index', 'surprises.letter_view', 'surprises.letters_index', 'surprises.open_when_index',
    'surprises.secret_box_index', 'smart.daily', 'smart.special_dates',
}


def _now():
    """Naive UTC 'now' (SQLite keeps naive datetimes; all our datetimes are UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notify(recipient_id, category, title, body=None, endpoint=None, params=None, actor_id=None):
    note = Notification(
        recipient_id=recipient_id, actor_id=actor_id, category=category,
        title=title[:200], body=(body or '')[:300] or None,
        link_endpoint=endpoint, link_params=json.dumps(params) if params else None,
    )
    db.session.add(note)
    db.session.commit()
    return note


def notify_chat_message(recipient_id, sender_id, sender_name, message_type):
    """ONE collapsed 'chat_message' notification per unread streak (not one per message)."""
    what = {'image': 'sent you a photo.', 'voice': 'sent you a voice message.'}.get(message_type, 'sent you a message.')
    existing = Notification.query.filter_by(
        recipient_id=recipient_id, category='chat_message', is_read=False).first()
    if existing:
        found = re.match(r'(\d+) new messages', existing.body or '')
        count = (int(found.group(1)) if found else 1) + 1
        existing.title = f'New messages from {sender_name}'
        existing.body = f'{count} new messages'
        existing.created_at = _now()
        db.session.commit()
        return existing
    return notify(recipient_id, 'chat_message', f'New message from {sender_name}',
                  f'{sender_name} {what}', endpoint='chat.index', actor_id=sender_id)


def mark_chat_notifications_read(user_id):
    rows = Notification.query.filter_by(recipient_id=user_id, category='chat_message', is_read=False).all()
    for note in rows:
        note.mark_read()
    if rows:
        db.session.commit()


def unread_count(user_id):
    return Notification.query.filter_by(recipient_id=user_id, is_read=False).count()


def unread_chat_count(user_id):
    return Notification.query.filter_by(recipient_id=user_id, category='chat_message', is_read=False).count()


def notification_url(note):
    """Safe link: whitelisted endpoint only, and a letter link only if the user may open that letter."""
    fallback = url_for('notifications.notifications_page')
    if note.link_endpoint not in ALLOWED_LINKS:
        return fallback
    try:
        if note.link_endpoint == 'surprises.letter_view':
            params = json.loads(note.link_params or '{}')
            letter = db.session.get(SecretLetter, int(params.get('letter_id')))
            if letter and note.recipient_id in (letter.user_id, letter.recipient_id):
                return url_for('surprises.letter_view', letter_id=letter.id)
            return url_for('surprises.letters_index')
        return url_for(note.link_endpoint)
    except Exception:
        return fallback


_UNLOCK_TITLES = {
    'letter': 'A letter has unlocked',
    'open_when': 'An "Open When" envelope has unlocked',
    'secret_box': 'A Secret Box surprise has unlocked',
}


def ensure_generated_notifications(user_id):
    """
    Notifications that come from the CALENDAR (no action by anybody):
      - a surprise addressed to this user reached its unlock date
      - a special date is today / tomorrow
    Runs lazily whenever the bell refreshes, so no background scheduler is needed.
    """
    created = False
    today_utc = _now().date()

    # --- unlocked surprises (once per letter) ---
    already = set()
    for note in Notification.query.filter_by(recipient_id=user_id, category='unlock').all():
        try:
            already.add(json.loads(note.link_params or '{}').get('letter_id'))
        except ValueError:
            pass
    senders = {u.id: u.name for u in User.query.all()}
    letters = SecretLetter.query.filter(
        SecretLetter.recipient_id == user_id,
        SecretLetter.unlock_date.isnot(None),
        SecretLetter.unlock_date <= today_utc,
    ).all()
    for letter in letters:
        if letter.id in already:
            continue
        if letter.created_at and letter.unlock_date <= letter.created_at.date():
            continue  # it was never locked, nothing "unlocked"
        db.session.add(Notification(
            recipient_id=user_id, actor_id=letter.user_id, category='unlock',
            title=_UNLOCK_TITLES.get(letter.category, 'A surprise has unlocked'),
            body=f'From {senders.get(letter.user_id, "your person")}.',
            link_endpoint='surprises.letter_view', link_params=json.dumps({'letter_id': letter.id})))
        created = True

    # --- special dates today / tomorrow (same title is not repeated within 20 hours) ---
    recent_titles = {n.title for n in Notification.query.filter(
        Notification.recipient_id == user_id, Notification.category == 'special_date',
        Notification.created_at >= _now() - timedelta(hours=20)).all()}
    local_today = date.today()
    for sd in SpecialDate.query.all():
        days = sd.days_until(local_today)
        if days not in (0, 1):
            continue
        title = f'{sd.title} is {"today" if days == 0 else "tomorrow"}'
        if title in recent_titles:
            continue
        db.session.add(Notification(
            recipient_id=user_id, category='special_date', title=title[:200],
            link_endpoint='smart.special_dates'))
        recent_titles.add(title)
        created = True

    if created:
        db.session.commit()
