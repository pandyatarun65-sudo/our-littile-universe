import os
import uuid
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


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


def _upload_dir():
    return os.path.join(current_app.static_folder, 'uploads')


def save_uploaded_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    if not allowed_file(file_storage.filename):
        return None

    # Phase 7: check the real content too, not only the extension.
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    ext = detect_image_type(head)
    if ext is None:
        return None

    safe_name = f"{uuid.uuid4().hex}.{ext}"      # our own name, our own (verified) extension

    upload_dir = _upload_dir()
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, safe_name))

    return f"uploads/{safe_name}"


def delete_photo_file(relative_path):
    if not relative_path:
        return
    # Phase 7: only ever delete files that are really inside the uploads folder.
    upload_dir = os.path.realpath(_upload_dir())
    full_path = os.path.realpath(os.path.join(current_app.static_folder, relative_path))
    if os.path.commonpath([upload_dir, full_path]) != upload_dir:
        return
    if os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass
