"""
app/utils/helpers.py — Shared utility functions used across the application.
"""

import os
import uuid
import re
import logging
from datetime import datetime, timezone
from bson import ObjectId  # installed as part of pymongo — do NOT install standalone bson package
from flask import jsonify

logger = logging.getLogger(__name__)


# ─── Standard API Response Helpers ────────────────────────────────────────────

def success_response(message: str, data=None, status_code: int = 200):
    """Return a standardised JSON success response."""
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def error_response(message: str, error_code: str = "ERROR", status_code: int = 400):
    """Return a standardised JSON error response."""
    payload = {
        "success": False,
        "message": message,
        "error": error_code,
    }
    return jsonify(payload), status_code


# ─── ObjectId / Serialisation ─────────────────────────────────────────────────

def object_id_to_str(obj):
    """
    Recursively convert ObjectId and datetime values in a dict/list to strings
    so they can be safely JSON-serialised.
    """
    if isinstance(obj, list):
        return [object_id_to_str(item) for item in obj]
    if isinstance(obj, dict):
        return {k: object_id_to_str(v) for k, v in obj.items()}
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def is_valid_object_id(oid: str) -> bool:
    """Check whether a string is a valid MongoDB ObjectId."""
    try:
        ObjectId(oid)
        return True
    except Exception:
        return False


# ─── Date / Time ──────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def parse_date(date_str: str) -> datetime | None:
    """Parse an ISO date string; return None on failure."""
    try:
        return datetime.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


# ─── File Upload Helpers ───────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


def allowed_file(filename: str) -> bool:
    """Return True if the file extension is in ALLOWED_EXTENSIONS."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename_unique(filename: str) -> str:
    """Generate a UUID-based filename preserving the original extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"{uuid.uuid4().hex}.{ext}"


def save_uploaded_file(file, upload_folder: str) -> str | None:
    """
    Save a validated file object to upload_folder.
    Returns the relative path string or None on failure.
    """
    if not file or not allowed_file(file.filename):
        return None
    unique_name = secure_filename_unique(file.filename)
    os.makedirs(upload_folder, exist_ok=True)
    save_path = os.path.join(upload_folder, unique_name)
    file.save(save_path)
    return save_path


# ─── Validation Helpers ────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-]{7,15}$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def is_valid_phone(phone: str) -> bool:
    return bool(PHONE_RE.match(phone or ""))


def validate_required_fields(data: dict, fields: list[str]) -> list[str]:
    """Return a list of missing field names."""
    return [f for f in fields if not data.get(f)]


# ─── Pagination ───────────────────────────────────────────────────────────────

def paginate(query_cursor, page: int = 1, per_page: int = 20) -> dict:
    """
    Apply skip/limit to a PyMongo cursor and return a pagination envelope.
    """
    page = max(1, page)
    per_page = min(max(1, per_page), 100)  # cap at 100

    total = query_cursor.count()          # deprecated in newer drivers — see note
    items = list(query_cursor.skip((page - 1) * per_page).limit(per_page))

    return {
        "items": object_id_to_str(items),
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def get_pagination_params(request) -> tuple[int, int]:
    """Extract page and per_page from a Flask request's query string."""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except (ValueError, TypeError):
        page, per_page = 1, 20
    return page, per_page
