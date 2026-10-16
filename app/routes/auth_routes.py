"""
app/routes/auth_routes.py — Authentication API routes (Phase 2 implementation).

Endpoints:
  POST   /api/auth/register      — Create new user account
  POST   /api/auth/login         — Login, receive JWT pair
  POST   /api/auth/logout        — Revoke access token
  GET    /api/auth/me            — Get current user profile
  PUT    /api/auth/me            — Update profile fields
  PUT    /api/auth/me/password   — Change password
  POST   /api/auth/refresh       — Issue new access token from refresh token
"""

from flask import Blueprint, request
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)

from app.utils import success_response, error_response
from app.database import DatabaseUnavailableError
from app.services.auth_service import (
    register_user,
    login_user,
    revoke_token,
    get_user_by_id,
    update_user_profile,
    change_password,
)

auth_bp = Blueprint("auth", __name__)


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    try:
        user, err = register_user(data)
    except DatabaseUnavailableError as exc:
        return error_response("Database unavailable — the server cannot accept registrations right now. Please try again later.", "DB_UNAVAILABLE", 503)
    if err:
        return error_response(err, "REGISTRATION_ERROR", 400)
    return success_response("Account created successfully.", data={"user": user}, status_code=201)


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate user and return JWT access + refresh tokens."""
    data     = request.get_json(silent=True) or {}
    email    = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return error_response("Email and password are required.", "MISSING_FIELDS", 400)

    try:
        payload, err = login_user(email, password)
    except DatabaseUnavailableError:
        return error_response(
            "Database unavailable — please ensure MongoDB is running and try again.",
            "DB_UNAVAILABLE", 503
        )
    except Exception as exc:
        return error_response("An unexpected server error occurred.", "INTERNAL_ERROR", 500)

    if err:
        return error_response(err, "AUTH_ERROR", 401)

    return success_response("Login successful.", data=payload, status_code=200)



# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True)
def logout():
    """Revoke the current access token (if present)."""
    try:
        verify_jwt_in_request(optional=True)
        jwt_payload = get_jwt()
        if jwt_payload:
            revoke_token(jwt_payload)
    except Exception:
        pass
    return success_response("Logged out successfully.", status_code=200)


# ── Current User (GET) ────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the authenticated user's profile."""
    user_id = get_jwt_identity()
    user    = get_user_by_id(user_id)
    if not user:
        return error_response("User not found.", "NOT_FOUND", 404)
    return success_response("User profile retrieved.", data={"user": user})


# ── Update Profile (PUT) ──────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update mutable profile fields (name, phone, address, pincode)."""
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}
    user, err = update_user_profile(user_id, data)
    if err:
        return error_response(err, "UPDATE_ERROR", 400)
    return success_response("Profile updated successfully.", data={"user": user})


# ── Change Password (PUT) ─────────────────────────────────────────────────────

@auth_bp.route("/me/password", methods=["PUT"])
@jwt_required()
def update_password():
    """Change the authenticated user's password."""
    user_id = get_jwt_identity()
    data    = request.get_json(silent=True) or {}

    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    ok, err = change_password(user_id, old_password, new_password)
    if not ok:
        return error_response(err, "PASSWORD_ERROR", 400)
    return success_response("Password changed successfully.")


# ── Token Refresh ─────────────────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Issue a new access token using a valid refresh token."""
    from flask_jwt_extended import create_access_token
    user_id = get_jwt_identity()
    claims  = get_jwt()

    additional = {k: claims[k] for k in ("role", "name", "email") if k in claims}
    new_token   = create_access_token(identity=user_id, additional_claims=additional)
    return success_response("Token refreshed.", data={"access_token": new_token})

