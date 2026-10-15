"""Persistent PRIVATE file storage.

Backend automatic chunta hai:
  * STORAGE_BUCKET set ho  -> S3-compatible bucket (Cloudflare R2, Supabase S3, B2...)
  * warna                  -> database table `media_blobs` (production me Neon, laptop par SQLite)
Files kabhi public nahi hoti: sirf login-protected Flask routes se milti hain.

Images (jpg/png/webp) put() me hi automatically resize + compress hoti hain,
isliye memory upload aur chat upload dono ek hi jagah se fayda uthate hain.
"""
import io
import logging
import os

from flask import send_file

log = logging.getLogger(__name__)
_client = None

MAX_IMAGE_SIDE = 1600          # longest side in pixels
IMAGE_QUALITY = 80             # JPEG / WebP quality
SKIP_BELOW_BYTES = 200 * 1024  # already small -> leave as is
_IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp')
_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')


def _use_s3():
    return bool(os.environ.get('STORAGE_BUCKET'))


def _s3():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config
        _client = boto3.client(
            's3',
            endpoint_url=os.environ.get('STORAGE_ENDPOINT') or None,
            aws_access_key_id=os.environ['STORAGE_ACCESS_KEY'],
            aws_secret_access_key=os.environ['STORAGE_SECRET_KEY'],
            region_name=os.environ.get('STORAGE_REGION') or 'auto',
            config=Config(signature_version='s3v4',
                          s3={'addressing_style': 'path'},
                          retries={'max_attempts': 3}),
        )
    return _client


def _shrink_image(data, content_type, key):
    """Resize (max 1600px) + recompress. Same format as the original, so the
    file extension / mimetype stored elsewhere stays correct. EXIF (incl. GPS)
    is dropped after fixing rotation. On any problem the original is returned."""
    ext = os.path.splitext(key or '')[1].lower()
    is_image = (content_type or '').lower() in _IMAGE_TYPES or ext in _IMAGE_EXTS
    if not is_image or len(data) < SKIP_BELOW_BYTES:
        return data
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP') or getattr(img, 'is_animated', False):
            return data
        if fmt == 'JPEG':
            img.draft('RGB', (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))   # fast, low-memory decode
        img = ImageOps.exif_transpose(img)
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)
        out = io.BytesIO()
        if fmt == 'JPEG':
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            img.save(out, 'JPEG', quality=IMAGE_QUALITY, optimize=True, progressive=True)
        elif fmt == 'WEBP':
            img.save(out, 'WEBP', quality=IMAGE_QUALITY, method=4)
        else:
            img.save(out, 'PNG', optimize=True)
        shrunk = out.getvalue()
        return shrunk if len(shrunk) < len(data) else data
    except Exception:
        log.warning('image shrink failed; storing original')
        return data


def put(key, data, content_type=None):
    """Bytes (ya file object) ko key ke naam se save karo."""
    if hasattr(data, 'read'):
        data = data.read()
    data = _shrink_image(data, content_type, key)
    if _use_s3():
        extra = {'ContentType': content_type} if content_type else {}
        _s3().put_object(Bucket=os.environ['STORAGE_BUCKET'], Key=key, Body=data, **extra)
        return
    from app import db
    from app.models import MediaBlob
    row = db.session.get(MediaBlob, key)
    if row is None:
        db.session.add(MediaBlob(key=key, data=data, content_type=content_type))
    else:
        row.data = data
        row.content_type = content_type
    db.session.commit()


def get(key):
    """Bytes return karta hai, ya None agar file nahi mili."""
    if _use_s3():
        from botocore.exceptions import ClientError
        try:
            return _s3().get_object(Bucket=os.environ['STORAGE_BUCKET'], Key=key)['Body'].read()
        except ClientError as exc:
            if exc.response.get('Error', {}).get('Code') in ('NoSuchKey', '404', 'NotFound'):
                return None
            raise
    from app import db
    from app.models import MediaBlob
    row = db.session.get(MediaBlob, key)
    return bytes(row.data) if row else None


def delete(key):
    if not key:
        return
    try:
        if _use_s3():
            _s3().delete_object(Bucket=os.environ['STORAGE_BUCKET'], Key=key)
            return
        from app import db
        from app.models import MediaBlob
        row = db.session.get(MediaBlob, key)
        if row is not None:
            db.session.delete(row)
            db.session.commit()
    except Exception:
        log.warning('storage delete failed')       # key/URL log nahi karte


def send(key, mimetype=None):
    """Login-protected route ke andar file stream karo (audio seeking ke liye range support). Nahi mili to None."""
    data = get(key)
    if data is None:
        return None
    response = send_file(io.BytesIO(data), mimetype=mimetype or 'application/octet-stream',
                         conditional=True, etag=False, max_age=0)
    # Keys random hote hain (file kabhi in-place change nahi hoti) -> browser 7 din cache kar sakta hai.
    # 'private' = shared proxies/CDN me kabhi nahi.
    response.headers['Cache-Control'] = 'private, max-age=604800'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response