"""
config.py — Application configuration classes.

Loaded by the Flask application factory via app.config.from_object().
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env before reading environment variables
load_dotenv()


class BaseConfig:
    """Shared settings across all environments."""

    # ── Flask ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-key")
    APP_NAME: str = os.getenv("APP_NAME", "Medicine Platform")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:5000")

    # ── JWT ────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "fallback-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = False  # Set True in production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_COOKIE_SAMESITE = "Lax"

    # ── MongoDB ────────────────────────────────────────────────────────────────
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/medicine_platform")
    MAP_API_KEY: str = os.getenv("MAP_API_KEY", "")
    MAP_API_PROVIDER: str = os.getenv("MAP_API_PROVIDER", "google").strip().lower()

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "static/uploads")
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_FILE_SIZE", 5 * 1024 * 1024))  # 5 MB
    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_STORAGE_URL = "memory://"


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False


class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    MONGO_URI = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/medicine_test")
    JWT_COOKIE_CSRF_PROTECT = False  # Simplify testing


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True


# Mapping string names to config objects — used by the factory
config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
