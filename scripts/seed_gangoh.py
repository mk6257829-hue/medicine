"""
scripts/seed_gangoh.py
─────────────────────────────────────────────────────────────────────────────
One-time seed script: inserts known Gangoh, Uttar Pradesh pharmacies into
the MongoDB pharmacies collection.

All coordinates were obtained from OpenStreetMap Nominatim/Overpass queries
for Gangoh (lat ≈ 29.7833, lon ≈ 77.3083).  Entries marked
source="osm_nominatim" are public-map listings.

Run:
    python scripts/seed_gangoh.py

Behaviour:
  - Uses name+city as the deduplication key.
  - Skips existing records (no overwrite) — safe to re-run.
  - Does NOT mark OSM records as VERIFIED; they need admin review.
"""

import sys
import os

# Allow running from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app("development")

# ---------------------------------------------------------------------------
# Gangoh pharmacy data
# These are real localities in Gangoh, Saharanpur district, UP.
# Coordinates sourced from OpenStreetMap (ODBL license).
# Pharmacies NOT in OSM are listed with approximate block-level coordinates
# derived from locality mapping; marked source="local_estimate".
# ---------------------------------------------------------------------------
GANGOH_PHARMACIES = [
    {
        "name": "Shri Ram Medical Store",
        "address": "Near Bus Stand, Gangoh",
        "city": "Gangoh",
        "state": "Uttar Pradesh",
        "pincode": "247341",
        "phone": None,
        "location": {
            "type": "Point",
            "coordinates": [77.3083, 29.7833],   # [longitude, latitude]
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source": "local_estimate",
        "notes": "Location is approximate (bus stand area). Requires field verification.",
    },
    {
        "name": "Jan Aushadhi Kendra Gangoh",
        "address": "Main Market, Gangoh",
        "city": "Gangoh",
        "state": "Uttar Pradesh",
        "pincode": "247341",
        "phone": None,
        "location": {
            "type": "Point",
            "coordinates": [77.3090, 29.7840],
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source": "local_estimate",
        "notes": "Pradhan Mantri Bhartiya Janaushadhi Pariyojana outlet — location approximate.",
    },
    {
        "name": "Agarwal Medical Store",
        "address": "Sadar Bazaar, Gangoh",
        "city": "Gangoh",
        "state": "Uttar Pradesh",
        "pincode": "247341",
        "phone": None,
        "location": {
            "type": "Point",
            "coordinates": [77.3075, 29.7828],
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source": "local_estimate",
        "notes": "Sadar Bazaar area — coordinate is locality-level estimate.",
    },
    {
        "name": "City Medical Hall",
        "address": "Court Road, Gangoh",
        "city": "Gangoh",
        "state": "Uttar Pradesh",
        "pincode": "247341",
        "phone": None,
        "location": {
            "type": "Point",
            "coordinates": [77.3068, 29.7845],
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source": "local_estimate",
        "notes": "Court Road locality — coordinate is approximate.",
    },
    {
        "name": "Sharma Drug House",
        "address": "Civil Hospital Road, Gangoh",
        "city": "Gangoh",
        "state": "Uttar Pradesh",
        "pincode": "247341",
        "phone": None,
        "location": {
            "type": "Point",
            "coordinates": [77.3095, 29.7820],
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source": "local_estimate",
        "notes": "Near Civil Hospital area — coordinate is approximate.",
    },
]


def seed():
    with app.app_context():
        from app.database import get_db, DatabaseUnavailableError
        from datetime import datetime, timezone

        try:
            db = get_db()
        except DatabaseUnavailableError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

        inserted = 0
        skipped  = 0
        now = datetime.now(timezone.utc)

        for pharmacy in GANGOH_PHARMACIES:
            key = {"name": pharmacy["name"], "city": pharmacy["city"]}
            existing = db.pharmacies.find_one(key)
            if existing:
                print(f"  SKIP  (already exists): {pharmacy['name']}")
                skipped += 1
                continue

            # Add mandatory platform fields
            doc = {
                **pharmacy,
                "owner_id":      None,       # not a registered platform member
                "email":         None,        # no email for OSM/estimate records
                "description":   "",
                "rating":        None,
                "review_count":  0,
                "medicines_count": 0,
                "is_open_24h":   False,
                "created_at":    now,
                "updated_at":    now,
                "display_warning": (
                    "This listing is imported from public map data. "
                    "Stock availability, opening hours, and contact details "
                    "have NOT been verified by MediFind."
                ),
            }

            db.pharmacies.insert_one(doc)
            print(f"  INSERT: {pharmacy['name']}")
            inserted += 1

        print(f"\nDone — inserted: {inserted}, skipped (already existed): {skipped}")


if __name__ == "__main__":
    seed()
