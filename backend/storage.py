"""Object storage for image assets (§3.2) — S3-compatible MinIO.

Image bytes live in MinIO, not in the database: uploads are parsed from a data URL, stored
under a per-owner key, and streamed back on demand. Falls back cleanly (available() == False)
when MinIO isn't configured so the app still boots.
"""
import os
import io
import base64
import hashlib

try:
    from minio import Minio
except Exception:  # pragma: no cover
    Minio = None

_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "127.0.0.1:9100")
_KEY = os.environ.get("MINIO_ACCESS_KEY")
_SECRET = os.environ.get("MINIO_SECRET_KEY")
_BUCKET = os.environ.get("MINIO_BUCKET", "visionlab-assets")
_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"

_client = None
if Minio and _KEY and _SECRET:
    try:
        _client = Minio(_ENDPOINT, access_key=_KEY, secret_key=_SECRET, secure=_SECURE)
        if not _client.bucket_exists(_BUCKET):
            _client.make_bucket(_BUCKET)
    except Exception:
        _client = None


def available():
    return _client is not None


def put_data_url(owner, data_url):
    """Store a base64 image data URL as an object; return its metadata (no bytes)."""
    header, b64 = (data_url.split(",", 1) + [""])[:2] if "," in data_url else ("", data_url)
    mime = "image/png"
    if header.startswith("data:"):
        mime = header[5:].split(";")[0] or "image/png"
    raw = base64.b64decode(b64)
    sha = hashlib.sha256(raw).hexdigest()[:32]
    key = f"{owner or 'seed'}/{sha}"
    _client.put_object(_BUCKET, key, io.BytesIO(raw), len(raw), content_type=mime)
    return {"object_key": key, "sha256": sha, "size_bytes": len(raw), "mime": mime}


def get_data_url(object_key, mime="image/png"):
    resp = _client.get_object(_BUCKET, object_key)
    try:
        raw = resp.read()
    finally:
        resp.close(); resp.release_conn()
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def delete(object_key):
    try:
        _client.remove_object(_BUCKET, object_key)
    except Exception:
        pass
