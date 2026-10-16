"""Idempotently seed the Gangoh medical-store directory.

The original request mentioned an initial list, but no records were provided.
Keep this list empty until a verifiable source list is supplied; never invent
businesses, contact details, hours, or coordinates. Each supplied record must
include a stable source_id and source so reruns upsert instead of duplicating.

Run: python scripts/seed_medical_stores.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app import create_app

# Add only records backed by an explicit, reviewable source.
INITIAL_STORES = []


def seed():
    app = create_app("development")
    with app.app_context():
        from app.database import DatabaseUnavailableError, get_db
        from app.models.medical_store import normalize_store

        try:
            collection = get_db().medical_stores
        except DatabaseUnavailableError as exc:
            raise SystemExit(f"ERROR: {exc}")

        inserted = updated = 0
        for entry in INITIAL_STORES:
            if not entry.get("source") or not entry.get("source_id"):
                raise ValueError("Every seed record needs stable source and source_id fields.")
            doc = normalize_store(entry)
            doc["created_at"] = datetime.now(timezone.utc)
            result = collection.update_one(
                {"source": doc["source"], "source_id": doc["source_id"]},
                {"$setOnInsert": doc},
                upsert=True,
            )
            inserted += int(result.upserted_id is not None)
            updated += int(result.matched_count > 0)
        print(f"Medical-store seed complete: inserted {inserted}, already present {updated}.")
        if not INITIAL_STORES:
            print("No seed entries added: the initial store list was not included in the request.")


if __name__ == "__main__":
    seed()
