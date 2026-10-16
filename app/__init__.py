"""
app/__init__.py — Flask Application Factory.

Usage:
    from app import create_app
    app = create_app()          # uses FLASK_ENV or 'default'
    app = create_app('testing') # explicit environment
"""

import os
import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import config_map
from app.database import init_db

# ── Module-level singletons (initialised inside factory) ──────────────────────
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)


def create_app(env: str | None = None) -> Flask:
    """
    Flask application factory.

    Args:
        env: One of 'development', 'testing', 'production', or None
             (falls back to FLASK_ENV env var, then 'default').
    Returns:
        A configured Flask application instance.
    """
    if env is None:
        env = os.getenv("FLASK_ENV", "default")

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # ── Configuration ──────────────────────────────────────────────────────────
    cfg = config_map.get(env, config_map["default"])
    app.config.from_object(cfg)

    # ── Logging ────────────────────────────────────────────────────────────────
    _configure_logging(app)

    # ── Extensions ────────────────────────────────────────────────────────────
    jwt.init_app(app)
    limiter.init_app(app)

    CORS(
        app,
        origins=app.config.get("CORS_ORIGINS", ["http://localhost:5000"]),
        supports_credentials=True,
    )

    # ── Database ───────────────────────────────────────────────────────────────
    init_db(app)

    # ── Ensure upload folder exists ────────────────────────────────────────────
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Blueprints ─────────────────────────────────────────────────────────────
    _register_blueprints(app)

    # ── JWT error handlers ─────────────────────────────────────────────────────
    _register_jwt_callbacks(jwt)

    # ── Global error handlers ─────────────────────────────────────────────────
    _register_error_handlers(app)

    app.logger.info("App created in '%s' mode.", env)
    return app


# ─── Private helpers ───────────────────────────────────────────────────────────

def _configure_logging(app: Flask):
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _register_blueprints(app: Flask):
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.medicine_routes import medicine_bp
    from app.routes.pharmacy_routes import pharmacy_bp
    from app.routes.inventory_routes import inventory_bp
    from app.routes.order_routes import order_bp
    from app.routes.prescription_routes import prescription_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.search_routes import search_bp
    from app.routes.medical_store_routes import medical_store_bp

    app.register_blueprint(main_bp)                           # /
    app.register_blueprint(auth_bp,         url_prefix="/api/auth")
    app.register_blueprint(user_bp,         url_prefix="/api/users")
    app.register_blueprint(medicine_bp,     url_prefix="/api/medicines")
    app.register_blueprint(pharmacy_bp,     url_prefix="/api/pharmacies")
    app.register_blueprint(inventory_bp,    url_prefix="/api/inventory")
    app.register_blueprint(order_bp,        url_prefix="/api/orders")
    app.register_blueprint(prescription_bp, url_prefix="/api/prescriptions")
    app.register_blueprint(admin_bp,        url_prefix="/api/admin")
    app.register_blueprint(search_bp,       url_prefix="/api/search")
    app.register_blueprint(medical_store_bp, url_prefix="/api/medical-stores")


def _register_jwt_callbacks(jwt: JWTManager):
    from flask import jsonify

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"success": False, "message": reason, "error": "UNAUTHORIZED"}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({"success": False, "message": reason, "error": "INVALID_TOKEN"}), 422

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has expired.", "error": "TOKEN_EXPIRED"}), 401

    @jwt.revoked_token_loader
    def revoked_token(jwt_header, jwt_payload):
        return jsonify({"success": False, "message": "Token has been revoked.", "error": "TOKEN_REVOKED"}), 401

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        from app.services.auth_service import is_token_revoked
        return is_token_revoked(jwt_payload)


def _register_error_handlers(app: Flask):
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"success": False, "message": str(e), "error": "BAD_REQUEST"}), 400

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"success": False, "message": "Forbidden.", "error": "FORBIDDEN"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found.", "error": "NOT_FOUND"}), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return jsonify({"success": False, "message": "File too large.", "error": "FILE_TOO_LARGE"}), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({"success": False, "message": "Too many requests.", "error": "RATE_LIMITED"}), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Internal server error: %s", e)
        return jsonify({"success": False, "message": "Internal server error.", "error": "INTERNAL_ERROR"}), 500
