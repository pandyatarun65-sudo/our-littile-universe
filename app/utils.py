import os
import re
import uuid

from app import storage

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
PHOTO_NAME_RE = re.compile(r'^[0-9a-f]{32}\.(jpg|png|gif|webp)$')
PHOTO_MIME = {'jpg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_image_type(head):
    """What the file REALLY is, judged from its first bytes (the extension can be faked)."""
    if head.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if head[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'webp'
    return None


def save_uploaded_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        return None

    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    ext = detect_image_type(head)
    if ext is None:
        return None

    safe_name = f"{uuid.uuid4().hex}.{ext}"      # our own name, our own (verified) extension
    storage.put(f"uploads/{safe_name}", file_storage.stream.read(), PHOTO_MIME[ext])

    return f"uploads/{safe_name}"                # web URL abhi bhi /static/uploads/<name> rehta hai


def delete_photo_file(relative_path):
    if not relative_path:
        return
    name = os.path.basename(relative_path)       # sirf file ka naam, database se path kabhi nahi
    if PHOTO_NAME_RE.match(name):
        storage.delete(f"uploads/{name}")