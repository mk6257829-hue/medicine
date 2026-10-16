"""
app/middleware/auth_middleware.py — Decorators for role-based access control.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

# ── Role constants ─────────────────────────────────────────────────────────────
ROLE_USER = "USER"
ROLE_PHARMACY_OWNER = "PHARMACY_OWNER"
ROLE_PHARMACIST = "PHARMACIST"
ROLE_ADMIN = "ADMIN"

ALL_ROLES = {ROLE_USER, ROLE_PHARMACY_OWNER, ROLE_PHARMACIST, ROLE_ADMIN}
PHARMACY_ROLES = {ROLE_PHARMACY_OWNER, ROLE_PHARMACIST}


def _make_forbidden(message: str):
    return jsonify({"success": False, "message": message, "error": "FORBIDDEN"}), 403


def require_auth(fn):
    """Any authenticated user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        return fn(*args, **kwargs)
    return wrapper


def require_roles(*roles):
    """Restrict access to one or more specific roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get("role", "")
            if user_role not in roles:
                return _make_forbidden(
                    f"Access denied. Required role(s): {', '.join(roles)}."
                )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(fn):
    """Admin-only access."""
    return require_roles(ROLE_ADMIN)(fn)


def require_pharmacy_staff(fn):
    """PHARMACY_OWNER or PHARMACIST access."""
    return require_roles(ROLE_PHARMACY_OWNER, ROLE_PHARMACIST)(fn)


def get_current_user_id() -> str:
    """Return the current JWT subject (user _id string)."""
    return get_jwt_identity()


def get_current_role() -> str:
    """Return the role from JWT claims."""
    return get_jwt().get("role", "")
