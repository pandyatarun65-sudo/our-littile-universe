"""
Chat helpers: media validation/storage, presence, typing, message status, JSON shape.
Works with the models in app/models.py (ChatMessage, User.last_seen).
"""
import os
import re
import time
import uuid
from datetime import datetime, timezone

from flask import current_app, url_for

from app import db
from app.models import ChatMessage, User
from app.notifications.services import mark_chat_notifications_read

MAX_TEXT_LEN = 4000
MAX_IMAGE_BYTES = 5 * 1024 * 1024     # also the app-wide MAX_CONTENT_LENGTH in config.py
MAX_VOICE_BYTES = 5 * 1024 * 1024
MAX_VOICE_SECONDS = 5 * 60
PAGE_SIZE = 30

ONLINE_SECONDS = 60          # active within 1 min   -> Online
RECENT_SECONDS = 10 * 60     # active within 10 min  -> "Last seen recently"
TYPING_SECONDS = 5           # the typing flag expires by itself

# Stored file names are ALWAYS 32 hex chars + a known extension, created by the server.
MEDIA_NAME_RE = re.compile(r'^[0-9a-f]{32}\.(jpg|png|gif|webp|webm|ogg|mp4)$')
MIME_BY_EXT = {
    'jpg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
    'webm': 'audio/webm', 'ogg': 'audio/ogg', 'mp4': 'audio/mp4',
}


# ------------------------------------------------------------------ time
def utcnow():
    """Naive UTC now (SQLite keeps naive datetimes; all our datetimes are UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(dt):
    """'2026-09-30T14:05:00Z' so the browser can show it in the user's own time zone."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None).isoformat(timespec='seconds') + 'Z'


# ------------------------------------------------------------------ users
def get_partner(user_id):
    """The ONE other user. The browser never tells us who the recipient is."""
    return User.query.filter(User.id != user_id).first()


# ------------------------------------------------------------------ private media
def chat_media_dir():
    """Outside app/static, so files can never be opened by a direct URL."""
    base = current_app.config.get('DATA_DIR') or current_app.instance_path
    return os.path.join(base, 'chat_media')


def media_ext(media_path):
    return media_path.rsplit('.', 1)[1] if media_path and '.' in media_path else ''


def sniff_image(head):
    """Look at the first bytes (what the file REALLY is), not at the file name."""
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp'
    return None


def sniff_audio(head):
    if head.startswith(b'\x1a\x45\xdf\xa3'):     # WebM (Chrome, Edge)
        return 'webm'
    if head.startswith(b'OggS'):                  # Ogg (Firefox)
        return 'ogg'
    if head[4:8] == b'ftyp':                      # MP4 / M4A (Safari)
        return 'mp4'
    return None


def save_media(file_storage, kind):
    """Validate + save an uploaded image/voice file. Returns (stored_filename, error_message)."""
    if not file_storage or not file_storage.filename:
        return None, 'No file received.'
    stream = file_storage.stream
    head = stream.read(16)
    stream.seek(0)
    ext = sniff_image(head) if kind == 'image' else sniff_audio(head)
    if not ext:
        return None, 'That file type is not supported.'
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    limit = MAX_IMAGE_BYTES if kind == 'image' else MAX_VOICE_BYTES
    if size == 0 or size > limit:
        return None, 'That file is empty or too large.'
    folder = chat_media_dir()
    os.makedirs(folder, exist_ok=True)
    filename = f'{uuid.uuid4().hex}.{ext}'          # our own name: the uploaded file name is ignored
    file_storage.save(os.path.join(folder, filename))
    return filename, None


def delete_media_file(media_path):
    if media_path and MEDIA_NAME_RE.match(media_path):
        path = os.path.join(chat_media_dir(), media_path)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def escape_like(text):
    """So that % and _ typed by the user are searched literally."""
    return text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


# ------------------------------------------------------------------ presence (User.last_seen)
def touch_presence(user_id, force=False):
    """'This user is active now'. One column on the user row, written at most every 10 s."""
    user = db.session.get(User, user_id)
    if user is None:
        return
    now = utcnow()
    last = user.last_seen.replace(tzinfo=None) if user.last_seen else None
    if force or last is None or (now - last).total_seconds() > 10:
        user.last_seen = now
        db.session.commit()


def presence_info(partner):
    """A state, plus a timestamp ONLY when the person is fully offline."""
    if partner is None or partner.last_seen is None:
        return {'state': 'offline', 'last_seen_at': None}
    last = partner.last_seen.replace(tzinfo=None)
    age = (utcnow() - last).total_seconds()
    if age <= ONLINE_SECONDS:
        return {'state': 'online', 'last_seen_at': None}
    if age <= RECENT_SECONDS:
        return {'state': 'recent', 'last_seen_at': None}
    return {'state': 'offline', 'last_seen_at': iso_utc(last)}


# ------------------------------------------------------------------ typing (memory only, never in the database)
_TYPING_UNTIL = {}     # user_id -> time.monotonic() when the flag expires
# Note: lives in the server process. Run ONE gunicorn worker (see README) so both users share it.


def set_typing(user_id, on):
    if on:
        _TYPING_UNTIL[user_id] = time.monotonic() + TYPING_SECONDS
    else:
        _TYPING_UNTIL.pop(user_id, None)


def partner_typing(partner_id):
    return _TYPING_UNTIL.get(partner_id, 0) > time.monotonic()


# ------------------------------------------------------------------ status: sent -> delivered -> seen
def mark_delivered(user_id):
    """The receiver's app is open and asked the server -> 'delivered'."""
    updated = (ChatMessage.query
               .filter(ChatMessage.recipient_id == user_id,
                       ChatMessage.delivered_at.is_(None),
                       ChatMessage.is_deleted.is_(False))
               .update({'delivered_at': utcnow()}, synchronize_session=False))
    if updated:
        db.session.commit()


def mark_seen(user_id, up_to_id):
    """The receiver is looking at the chat -> 'seen'."""
    mark_delivered(user_id)
    updated = (ChatMessage.query
               .filter(ChatMessage.recipient_id == user_id,
                       ChatMessage.id <= up_to_id,
                       ChatMessage.seen_at.is_(None),
                       ChatMessage.is_deleted.is_(False))
               .update({'seen_at': utcnow()}, synchronize_session=False))
    if updated:
        db.session.commit()
    mark_chat_notifications_read(user_id)


# ------------------------------------------------------------------ JSON shape sent to the browser
def _preview(msg):
    if msg.message_type == 'image':
        return 'Photo'
    if msg.message_type == 'voice':
        return 'Voice message'
    return (msg.body or '').replace('\n', ' ')[:80]


def serialize_message(msg, me_id):
    mine = msg.sender_id == me_id
    deleted = bool(msg.is_deleted)
    has_media = (not deleted) and msg.message_type in ('image', 'voice') and bool(msg.media_path)
    data = {
        'id': msg.id,
        'mine': mine,
        'kind': msg.message_type,
        'deleted': deleted,
        'body': None if deleted else msg.body,
        'created_at': iso_utc(msg.sent_at),
        'status': msg.status if (mine and not deleted) else None,
        'media_url': url_for('chat.media', message_id=msg.id) if has_media else None,
        'duration_ms': (msg.media_duration or 0) * 1000 if has_media and msg.message_type == 'voice' else None,
        'reply': None,
    }
    if msg.reply_to_id:
        original = msg.reply_to
        if original is None or original.is_deleted:
            data['reply'] = {'id': msg.reply_to_id, 'deleted': True}
        else:
            data['reply'] = {
                'id': original.id, 'deleted': False, 'kind': original.message_type,
                'mine': original.sender_id == me_id, 'preview': _preview(original),
            }
    return data
