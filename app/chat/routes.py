"""
Private two-person chat. Endpoints: chat.index, chat.media, ... (blueprint name: 'chat')

SECURITY RULES used in every route below:
  1. @login_required  (must be logged in)
  2. the recipient is decided by the SERVER (the one other user), never by the browser
  3. every message lookup is limited to messages where I am sender OR recipient
  4. only the sender may delete a message
  5. every POST checks the CSRF token (X-CSRF-Token header)
"""
from flask import Blueprint, abort, jsonify, render_template, request, send_from_directory
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app import db
from app.models import ChatMessage
from app.security import check_csrf
from app.notifications.services import notify_chat_message
from app.chat.services import (
    MAX_TEXT_LEN, MAX_VOICE_SECONDS, MEDIA_NAME_RE, MIME_BY_EXT, PAGE_SIZE,
    chat_media_dir, delete_media_file, escape_like, get_partner, iso_utc, mark_delivered,
    mark_seen, media_ext, partner_typing, presence_info, save_media, serialize_message,
    set_typing, touch_presence, utcnow,
)

chat_bp = Blueprint('chat', __name__)


def _partner_or_404():
    partner = get_partner(current_user.id)
    if partner is None:
        abort(404)
    return partner


def _my_messages():
    """Base query: ONLY messages I sent or received (this is what blocks IDOR)."""
    return ChatMessage.query.filter(
        db.or_(ChatMessage.sender_id == current_user.id,
               ChatMessage.recipient_id == current_user.id))


def _resolve_reply(raw_id):
    if raw_id in (None, '', 0):
        return None
    try:
        reply_id = int(raw_id)
    except (ValueError, TypeError):
        abort(400)
    original = _my_messages().filter(ChatMessage.id == reply_id).first()
    if original is None or original.is_deleted:
        abort(400)
    return original


def _create_message(partner, message_type, body=None, media_path=None, duration=None, reply_to=None):
    message = ChatMessage(
        sender_id=current_user.id, recipient_id=partner.id, message_type=message_type,
        body=body, media_path=media_path, media_duration=duration,
        reply_to_id=reply_to.id if reply_to else None,
    )
    db.session.add(message)
    db.session.commit()
    set_typing(current_user.id, False)             # sending ends "typing..."
    notify_chat_message(partner.id, current_user.id, current_user.name, message_type)
    return message


# ------------------------------------------------------------------ page
@chat_bp.route('/chat')
@login_required
def index():
    partner = _partner_or_404()
    touch_presence(current_user.id, force=True)
    return render_template('chat.html', partner=partner, me_id=current_user.id)


# ------------------------------------------------------------------ reading
@chat_bp.route('/chat/messages')
@login_required
def messages():
    """Latest page of messages, or older ones with ?before_id=."""
    _partner_or_404()
    before_id = request.args.get('before_id', type=int)
    query = _my_messages()
    if before_id:
        query = query.filter(ChatMessage.id < before_id)
    rows = (query.options(selectinload(ChatMessage.reply_to))
            .order_by(ChatMessage.id.desc()).limit(PAGE_SIZE + 1).all())
    has_more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE][::-1]
    mark_delivered(current_user.id)
    return jsonify(messages=[serialize_message(m, current_user.id) for m in rows],
                   has_more=has_more)


@chat_bp.route('/chat/poll')
@login_required
def poll():
    """One small request every ~3 s: new messages + status ticks + typing + presence."""
    partner = _partner_or_404()
    after_id = request.args.get('after_id', 0, type=int) or 0
    touch_presence(current_user.id)
    mark_delivered(current_user.id)

    incoming = (ChatMessage.query
                .options(selectinload(ChatMessage.reply_to))
                .filter(ChatMessage.sender_id == partner.id,
                        ChatMessage.recipient_id == current_user.id,
                        ChatMessage.id > after_id)
                .order_by(ChatMessage.id.asc()).limit(100).all())

    still_unseen = (ChatMessage.query
                    .filter(ChatMessage.sender_id == current_user.id,
                            ChatMessage.seen_at.is_(None),
                            ChatMessage.is_deleted.is_(False))
                    .order_by(ChatMessage.id.desc()).limit(50).all())

    deleted_ids = [row[0] for row in db.session.query(ChatMessage.id).filter(
        ChatMessage.sender_id == partner.id,
        ChatMessage.recipient_id == current_user.id,
        ChatMessage.is_deleted.is_(True),
    ).order_by(ChatMessage.id.desc()).limit(100)]

    return jsonify(
        messages=[serialize_message(m, current_user.id) for m in incoming],
        statuses=[{'id': m.id, 'status': m.status} for m in still_unseen],
        deleted_ids=deleted_ids,
        typing=partner_typing(partner.id),
        presence=presence_info(partner),
    )


@chat_bp.route('/chat/seen', methods=['POST'])
@login_required
def seen():
    check_csrf()
    data = request.get_json(silent=True) or {}
    up_to = data.get('up_to_id')
    if not isinstance(up_to, int) or isinstance(up_to, bool):
        abort(400)
    mark_seen(current_user.id, up_to)
    return jsonify(ok=True)


@chat_bp.route('/chat/typing', methods=['POST'])
@login_required
def typing():
    """Only sets a short-lived flag in memory. No message, no database row, no history."""
    check_csrf()
    _partner_or_404()
    set_typing(current_user.id, True)
    return ('', 204)


# ------------------------------------------------------------------ sending
@chat_bp.route('/chat/send', methods=['POST'])
@login_required
def send():
    check_csrf()
    partner = _partner_or_404()
    data = request.get_json(silent=True) or {}
    body = data.get('body')
    if not isinstance(body, str) or not body.strip():
        return jsonify(error='Write something first.'), 400
    body = body.strip()
    if len(body) > MAX_TEXT_LEN:
        return jsonify(error=f'Please keep a message under {MAX_TEXT_LEN} characters.'), 400
    reply_to = _resolve_reply(data.get('reply_to_id'))
    message = _create_message(partner, 'text', body=body, reply_to=reply_to)
    return jsonify(message=serialize_message(message, current_user.id)), 201


@chat_bp.route('/chat/send-media', methods=['POST'])
@login_required
def send_media():
    check_csrf()
    partner = _partner_or_404()
    kind = request.form.get('kind')
    if kind not in ('image', 'voice'):
        return jsonify(error='Unknown message type.'), 400

    reply_to = _resolve_reply(request.form.get('reply_to_id', type=int))

    stored_name, error = save_media(request.files.get('file'), kind)
    if error:
        return jsonify(error=error), 400

    duration = None
    if kind == 'voice':
        ms = request.form.get('duration_ms', 0, type=int) or 0
        duration = max(0, min(round(ms / 1000), MAX_VOICE_SECONDS))   # seconds, only used for display

    message = _create_message(partner, kind, media_path=stored_name, duration=duration, reply_to=reply_to)
    return jsonify(message=serialize_message(message, current_user.id)), 201


# ------------------------------------------------------------------ delete (soft delete)
@chat_bp.route('/chat/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    check_csrf()
    message = db.session.get(ChatMessage, message_id)
    if message is None or message.sender_id != current_user.id:
        abort(404)                       # not yours (or missing): same answer, no information leak
    if not message.is_deleted:
        delete_media_file(message.media_path)
        message.body = None
        message.media_path = None
        message.media_duration = None
        message.is_deleted = True
        db.session.commit()
    return jsonify(ok=True, message=serialize_message(message, current_user.id))


# ------------------------------------------------------------------ private media
@chat_bp.route('/chat/media/<int:message_id>')
@login_required
def media(message_id):
    message = db.session.get(ChatMessage, message_id)
    if message is None or current_user.id not in (message.sender_id, message.recipient_id):
        abort(404)
    if message.is_deleted or not message.media_path or not MEDIA_NAME_RE.match(message.media_path):
        abort(404)
    response = send_from_directory(
        chat_media_dir(), message.media_path,
        mimetype=MIME_BY_EXT.get(media_ext(message.media_path)),
        conditional=True)                # conditional = supports audio seeking
    response.headers['Cache-Control'] = 'private, max-age=3600'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


# ------------------------------------------------------------------ search
@chat_bp.route('/chat/search')
@login_required
def search():
    query = request.args.get('q', '').strip()[:100]
    if len(query) < 2:
        return jsonify(results=[])
    pattern = '%' + escape_like(query) + '%'
    rows = (_my_messages()
            .filter(ChatMessage.message_type == 'text', ChatMessage.is_deleted.is_(False),
                    ChatMessage.body.ilike(pattern, escape='\\'))
            .order_by(ChatMessage.id.desc()).limit(30).all())
    return jsonify(results=[{
        'id': m.id, 'mine': m.sender_id == current_user.id,
        'snippet': (m.body or '')[:140], 'created_at': iso_utc(m.sent_at),
    } for m in rows])
