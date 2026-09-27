import os
import uuid
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_photo(file_storage):
    if not file_storage or not file_storage.filename:
        return None

    filename = file_storage.filename
    if not allowed_file(filename):
        return None

    ext = filename.rsplit('.', 1)[1].lower()
    safe_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = os.path.join(current_app.static_folder, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    file_storage.save(os.path.join(upload_dir, safe_name))

    return f"uploads/{safe_name}"


def delete_photo_file(relative_path):
    if not relative_path:
        return
    full_path = os.path.join(current_app.static_folder, relative_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass