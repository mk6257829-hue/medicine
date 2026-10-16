"""
app/database/connection.py — MongoDB connection singleton.

Provides get_db() used throughout services and routes.
"""

import logging
from pymongo import MongoClient, ASCENDING, GEOSPHERE
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_client: MongoClient | None = None
_db = None


def init_db(app):
    """
    Initialise the MongoDB client using the app's MONGO_URI.
    Called once from the Flask application factory.
    """
    global _client, _db

    mongo_uri: str = app.config["MONGO_URI"]
    db_name = mongo_uri.split("/")[-1].split("?")[0] or "medicine_platform"

    try:
        _client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Verify connectivity eagerly
        _client.admin.command("ping")
        _db = _client[db_name]
        logger.info("MongoDB connected — database: %s", db_name)
        _create_indexes(_db)
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.warning(
            "MongoDB connection failed (running without DB — HTML pages will work, API routes may error): %s", exc
        )
        _client = None
        _db = None


class DatabaseUnavailableError(RuntimeError):
    """Raised when the MongoDB connection is not available."""
    pass


def get_db():
    """Return the active database handle.

    Raises DatabaseUnavailableError if MongoDB is not connected so callers
    can return a clean HTTP 503 instead of a generic 500.
    """
    if _db is None:
        raise DatabaseUnavailableError(
            "MongoDB is unavailable. Please ensure MongoDB is running on localhost:27017."
        )
    return _db


def close_db():
    """Gracefully close the MongoDB client."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


# ─── Index Creation ────────────────────────────────────────────────────────────

def _create_indexes(db):
    """Create all necessary indexes. Safe to call multiple times (idempotent)."""

    # users
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("phone", ASCENDING)])
    db.users.create_index([("role", ASCENDING)])
    db.users.create_index([("status", ASCENDING)])

    # medicines
    db.medicines.create_index([("name", ASCENDING)])
    db.medicines.create_index([("generic_name", ASCENDING)])
    db.medicines.create_index([("composition", ASCENDING)])
    db.medicines.create_index([("status", ASCENDING)])
    # Text index for full-text search
    db.medicines.create_index(
        [
            ("name", "text"),
            ("generic_name", "text"),
            ("composition", "text"),
            ("manufacturer", "text"),
        ],
        name="medicines_text_index",
        default_language="english",
    )

    # pharmacies
    db.pharmacies.create_index([("verification_status", ASCENDING)])
    db.pharmacies.create_index([("owner_id", ASCENDING)])
    db.pharmacies.create_index([("city", ASCENDING)])          # for city filter on map
    # Non-unique sparse index on email.
    # OSM-imported pharmacies have email=None; a unique index (even sparse)
    # collides when multiple null-email records exist. Uniqueness for registered
    # pharmacies is enforced in the registration application logic instead.
    try:
        db.pharmacies.drop_index("pharmacies_email_unique_sparse")
    except Exception:
        pass  # index may not exist yet
    db.pharmacies.create_index(
        [("email", ASCENDING)],
        sparse=True,
        name="pharmacies_email_sparse",
    )
    db.pharmacies.create_index([("location", GEOSPHERE)])   # 2dsphere for nearby search

    # Permanent, town-scoped medical-store directory (separate from platform pharmacies).
    db.medical_stores.create_index(
        [("source", ASCENDING), ("source_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"source_id": {"$type": "string"}},
        name="medical_stores_source_identity",
    )
    db.medical_stores.create_index([("dedupe_key", ASCENDING)], unique=True, name="medical_stores_dedupe_key")
    db.medical_stores.create_index([("latitude", ASCENDING), ("longitude", ASCENDING)], name="medical_stores_coordinates")

    # inventory
    db.inventory.create_index([("pharmacy_id", ASCENDING)])
    db.inventory.create_index([("medicine_id", ASCENDING)])
    db.inventory.create_index([("expiry_date", ASCENDING)])
    db.inventory.create_index([("status", ASCENDING)])
    db.inventory.create_index(
        [("pharmacy_id", ASCENDING), ("medicine_id", ASCENDING)],
        name="inventory_compound",
    )

    # orders
    db.orders.create_index([("user_id", ASCENDING)])
    db.orders.create_index([("pharmacy_id", ASCENDING)])
    db.orders.create_index([("status", ASCENDING)])
    db.orders.create_index([("created_at", ASCENDING)])

    # prescriptions
    db.prescriptions.create_index([("user_id", ASCENDING)])
    db.prescriptions.create_index([("pharmacy_id", ASCENDING)])
    db.prescriptions.create_index([("status", ASCENDING)])

    # notifications
    db.notifications.create_index([("user_id", ASCENDING)])
    db.notifications.create_index([("is_read", ASCENDING)])

    # audit_logs
    db.audit_logs.create_index([("user_id", ASCENDING)])
    db.audit_logs.create_index([("action", ASCENDING)])
    db.audit_logs.create_index([("created_at", ASCENDING)])

    logger.info("MongoDB indexes ensured.")
