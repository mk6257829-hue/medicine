"""
app/services/auth_service.py — Authentication business logic.

Responsibilities:
  - User registration with role validation
  - Login with password verification
  - JWT token generation with custom claims
  - Token revocation (blacklist via MongoDB)
  - Current-user retrieval
"""

import logging
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token

from app.database import get_db
from app.utils import is_valid_email, is_valid_phone, utcnow, object_id_to_str
from app.middleware.auth_middleware import ROLE_USER, ROLE_PHARMACY_OWNER

logger = logging.getLogger(__name__)

# Roles users can self-select at registration
SELF_REGISTER_ROLES = {ROLE_USER, ROLE_PHARMACY_OWNER}


# ─── Registration ──────────────────────────────────────────────────────────────

def register_user(data: dict) -> tuple:
    """
    Create a new user account.
    Returns (user_dict, None) on success or (None, error_message) on failure.
    """
    db = get_db()

    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip().lower()
    phone    = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    role     = (data.get("role") or ROLE_USER).strip().upper()

    # Validate
    if not name or len(name) < 2:
        return None, "Name must be at least 2 characters."
    if not email or not is_valid_email(email):
        return None, "A valid email address is required."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    if phone and not is_valid_phone(phone):
        return None, "Invalid phone number format."
    if role not in SELF_REGISTER_ROLES:
        return None, f"Invalid role. Choose one of: {', '.join(sorted(SELF_REGISTER_ROLES))}."

    if db.users.find_one({"email": email}):
        return None, "An account with this email already exists."

    now = utcnow()
    user_doc = {
        "name":          name,
        "email":         email,
        "phone":         phone,
        "password_hash": generate_password_hash(password),
        "role":          role,
        "status":        "ACTIVE",
        "avatar_url":    None,
        "address":       {},
        "pincode":       data.get("pincode", ""),
        "created_at":    now,
        "updated_at":    now,
        "last_login":    None,
        "pharmacy_id":   None,
    }

    result = db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    logger.info("New user registered: %s (role=%s)", email, role)
    return _sanitise_user(user_doc), None


# ─── Login ─────────────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> tuple:
    """
    Verify credentials and return token pair + user info.
    Returns (payload_dict, None) on success or (None, error_message) on failure.
    """
    db = get_db()
    email = (email or "").strip().lower()

    if not email or not password:
        return None, "Email and password are required."

    user = db.users.find_one({"email": email})
    if not user or not check_password_hash(user.get("password_hash", ""), password):
        return None, "Invalid email or password."

    if user.get("status") != "ACTIVE":
        return None, "Your account has been suspended. Please contact support."

    user_id_str = str(user["_id"])
    claims = {
        "role":  user["role"],
        "name":  user["name"],
        "email": user["email"],
    }

    access_token  = create_access_token(identity=user_id_str, additional_claims=claims)
    refresh_token = create_refresh_token(identity=user_id_str, additional_claims=claims)

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": utcnow(), "updated_at": utcnow()}},
    )

    logger.info("User logged in: %s", email)
    return {"access_token": access_token, "refresh_token": refresh_token, "user": _sanitise_user(user)}, None


# ─── Token Revocation ──────────────────────────────────────────────────────────

def revoke_token(jwt_payload: dict) -> None:
    """Blacklist a JWT by its JTI."""
    db = get_db()
    jti = jwt_payload.get("jti")
    if not jti:
        return
    db.token_blocklist.update_one(
        {"jti": jti},
        {"$set": {"jti": jti, "user_id": jwt_payload.get("sub"), "revoked_at": utcnow(), "exp": jwt_payload.get("exp")}},
        upsert=True,
    )


def is_token_revoked(jwt_payload: dict) -> bool:
    """Return True if the JWT JTI is in the blocklist."""
    db = get_db()
    return db.token_blocklist.find_one({"jti": jwt_payload.get("jti")}) is not None


# ─── User Retrieval ────────────────────────────────────────────────────────────

def get_user_by_id(user_id: str) -> dict | None:
    """Retrieve and sanitise a user by string ObjectId."""
    db = get_db()
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
    return _sanitise_user(user) if user else None


# ─── Profile Update ────────────────────────────────────────────────────────────

def update_user_profile(user_id: str, data: dict) -> tuple:
    """Update mutable profile fields. Returns (user_dict, None) or (None, error)."""
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return None, "Invalid user ID."

    allowed = {"name", "phone", "address", "pincode", "avatar_url"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return None, "No valid fields to update."
    if "phone" in updates and updates["phone"] and not is_valid_phone(updates["phone"]):
        return None, "Invalid phone number format."

    updates["updated_at"] = utcnow()
    db.users.update_one({"_id": oid}, {"$set": updates})
    updated = db.users.find_one({"_id": oid})
    return _sanitise_user(updated), None


# ─── Password Change ───────────────────────────────────────────────────────────

def change_password(user_id: str, old_password: str, new_password: str) -> tuple:
    """Verify old password, set new hash. Returns (True, None) or (False, error)."""
    db = get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        return False, "Invalid user ID."

    user = db.users.find_one({"_id": oid})
    if not user:
        return False, "User not found."
    if not check_password_hash(user.get("password_hash", ""), old_password):
        return False, "Current password is incorrect."
    if len(new_password) < 8:
        return False, "New password must be at least 8 characters."

    db.users.update_one(
        {"_id": oid},
        {"$set": {"password_hash": generate_password_hash(new_password), "updated_at": utcnow()}},
    )
    return True, None


# ─── Internal ──────────────────────────────────────────────────────────────────

def _sanitise_user(user: dict) -> dict:
    """Strip sensitive fields and serialise ObjectId/datetime."""
    if not user:
        return {}
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    return object_id_to_str(safe)
