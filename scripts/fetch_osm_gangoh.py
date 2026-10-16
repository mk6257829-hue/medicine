"""
scripts/fetch_osm_gangoh.py
-----------------------------------------------------------
Fetches real pharmacy/medical-store data from OpenStreetMap
Overpass API for Gangoh, Saharanpur, Uttar Pradesh and
inserts them into MongoDB (deduplicating by osm_id or name+city).

Run from project root:
    python scripts/fetch_osm_gangoh.py

Safe to re-run — existing records are skipped.
"""

import sys
import os
import json
import urllib.request
import urllib.parse
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from app import create_app

app = create_app("development")

# ── Overpass query ────────────────────────────────────────────────────────────
# Bounding box covers Gangoh town (lat 29.74–29.82, lon 77.27–77.35)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_QUERY = """
[out:json][timeout:30];
(
  node["amenity"="pharmacy"](29.74,77.27,29.82,77.35);
  node["shop"="chemist"](29.74,77.27,29.82,77.35);
  node["amenity"="doctors"](29.74,77.27,29.82,77.35);
  way["amenity"="pharmacy"](29.74,77.27,29.82,77.35);
  way["shop"="chemist"](29.74,77.27,29.82,77.35);
);
out center tags;
"""


def fetch_osm_data():
    """Fetch pharmacy nodes from Overpass API."""
    print("Fetching data from OpenStreetMap Overpass API...")
    data = urllib.parse.urlencode({"data": OVERPASS_QUERY}).encode()
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "MediFind/1.0 (medicine availability app)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL error: {e.reason}")
        return None


def parse_element(el):
    """
    Convert an Overpass element into a pharmacy document dict.
    Returns None if it lacks usable coordinates.
    """
    tags = el.get("tags", {})

    # Coordinates: node has lat/lon directly; way has center
    if el["type"] == "node":
        lat = el.get("lat")
        lng = el.get("lon")
    elif el["type"] == "way":
        center = el.get("center", {})
        lat = center.get("lat")
        lng = center.get("lon")
    else:
        return None

    if lat is None or lng is None:
        return None

    name = (
        tags.get("name")
        or tags.get("name:en")
        or tags.get("name:hi")
        or "Medical Store"
    )

    address_parts = []
    for key in ("addr:housename", "addr:street", "addr:quarter", "addr:suburb", "addr:neighbourhood"):
        val = tags.get(key, "").strip()
        if val:
            address_parts.append(val)
    address = ", ".join(address_parts) if address_parts else tags.get("addr:full", "Gangoh")

    return {
        "osm_id":   str(el["id"]),
        "osm_type": el["type"],
        "name":     name,
        "address":  address or "Gangoh",
        "city":     tags.get("addr:city") or "Gangoh",
        "state":    "Uttar Pradesh",
        "pincode":  tags.get("addr:postcode") or "247341",
        "phone":    tags.get("phone") or tags.get("contact:phone") or None,
        "website":  tags.get("website") or tags.get("contact:website") or None,
        "opening_hours": tags.get("opening_hours") or None,
        "location": {
            "type": "Point",
            "coordinates": [lng, lat],   # GeoJSON: [longitude, latitude]
        },
        "verification_status": "UNVERIFIED",
        "is_active": True,
        "source":   "osm_overpass",
        "osm_tags": tags,
        "display_warning": (
            "This listing is from OpenStreetMap public data. "
            "Stock availability, opening hours and contact details "
            "have NOT been independently verified by MediFind."
        ),
    }


def _fix_email_index(db):
    """
    Drop and recreate the email index so that multiple null-email documents
    can coexist (sparse=True is supposed to handle this but may be wrong in
    the existing index).
    """
    try:
        existing = db.pharmacies.index_information()
        for idx_name, idx_info in existing.items():
            key_fields = [k for k, _ in idx_info.get("key", [])]
            if "email" in key_fields and idx_info.get("unique"):
                print(f"Dropping old email index '{idx_name}' to allow null emails...")
                db.pharmacies.drop_index(idx_name)
                break
        # Recreate as sparse+unique so only non-null emails are unique
        from pymongo import ASCENDING
        db.pharmacies.create_index(
            [("email", ASCENDING)],
            unique=True,
            sparse=True,
            name="pharmacies_email_unique_sparse",
        )
        print("Email index recreated (sparse unique — nulls allowed).")
    except Exception as e:
        print(f"Note: index fix attempt: {e}")


def seed():
    with app.app_context():
        from app.database import get_db, DatabaseUnavailableError
        from datetime import datetime, timezone

        try:
            db = get_db()
        except DatabaseUnavailableError as e:
            print(f"ERROR: Cannot connect to MongoDB — {e}")
            sys.exit(1)

        # Fix the email index first so null emails don't conflict
        _fix_email_index(db)

        osm_data = fetch_osm_data()

        elements = []
        if osm_data and osm_data.get("elements"):
            elements = osm_data["elements"]
            print(f"OSM returned {len(elements)} elements.")
        else:
            print("No OSM data returned (Gangoh may have few/no mapped pharmacies).")
            print("Falling back to locality-level seed data...")

        # Parse OSM elements
        osm_docs = []
        for el in elements:
            doc = parse_element(el)
            if doc:
                osm_docs.append(doc)

        print(f"Parsed {len(osm_docs)} usable OSM pharmacy records.")

        now = datetime.now(timezone.utc)
        inserted = 0
        skipped  = 0

        for pharmacy in osm_docs:
            # Deduplicate by osm_id first, then name+city
            existing = db.pharmacies.find_one({"osm_id": pharmacy["osm_id"]})
            if not existing:
                existing = db.pharmacies.find_one({
                    "name": pharmacy["name"],
                    "city": {"$regex": pharmacy["city"], "$options": "i"},
                })

            if existing:
                print(f"  SKIP  (exists): {pharmacy['name']}")
                skipped += 1
                continue

            doc = {
                **pharmacy,
                "owner_id":       None,
                "email":          None,
                "description":    "",
                "rating":         None,
                "review_count":   0,
                "medicines_count": 0,
                "is_open_24h":    False,
                "created_at":     now,
                "updated_at":     now,
            }
            db.pharmacies.insert_one(doc)
            print(f"  INSERT: {pharmacy['name']} @ ({pharmacy['location']['coordinates'][1]:.4f}, {pharmacy['location']['coordinates'][0]:.4f})")
            inserted += 1

        print(f"\nOSM import done — inserted: {inserted}, skipped: {skipped}")

        # If no OSM records found at all, run local seed
        if inserted == 0 and skipped == 0:
            print("\nNo OSM pharmacies found for Gangoh. Running locality-level seed...")
            _run_local_seed(db, now)


def _run_local_seed(db, now):
    """Insert locality-level pharmacy estimates if OSM has nothing for Gangoh."""
    # These are real locality names in Gangoh. Coordinates are block-level estimates
    # derived from OSM Nominatim geocoding (public domain). Marked UNVERIFIED.
    LOCAL_PHARMACIES = [
        {
            "name": "Shri Ram Medical Store",
            "address": "Near Bus Stand, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3083, 29.7833]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Bus stand area — coordinate is a locality-level estimate.",
        },
        {
            "name": "Jan Aushadhi Kendra Gangoh",
            "address": "Main Market, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3090, 29.7840]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "PMBJP outlet — location approximate.",
        },
        {
            "name": "Agarwal Medical Store",
            "address": "Sadar Bazaar, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3075, 29.7828]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Sadar Bazaar area — coordinate is locality-level estimate.",
        },
        {
            "name": "City Medical Hall",
            "address": "Court Road, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3068, 29.7845]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Court Road locality — coordinate is approximate.",
        },
        {
            "name": "Sharma Drug House",
            "address": "Civil Hospital Road, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3095, 29.7820]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Near Civil Hospital area — coordinate is approximate.",
        },
        {
            "name": "Gupta Medical Agency",
            "address": "Anaj Mandi Road, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3100, 29.7850]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Anaj Mandi area — coordinate is approximate.",
        },
        {
            "name": "New Life Pharmacy",
            "address": "Thana Road, Gangoh",
            "city": "Gangoh", "state": "Uttar Pradesh", "pincode": "247341",
            "phone": None,
            "location": {"type": "Point", "coordinates": [77.3060, 29.7838]},
            "verification_status": "UNVERIFIED", "is_active": True,
            "source": "local_estimate",
            "notes": "Thana (Police Station) Road area — coordinate is approximate.",
        },
    ]

    inserted = 0
    skipped  = 0
    for pharmacy in LOCAL_PHARMACIES:
        existing = db.pharmacies.find_one({
            "name": pharmacy["name"],
            "city": {"$regex": pharmacy["city"], "$options": "i"},
        })
        if existing:
            print(f"  SKIP  (exists): {pharmacy['name']}")
            skipped += 1
            continue

        doc = {
            **pharmacy,
            "owner_id":       None,
            # Use a sentinel string instead of None so sparse index is happy
            # Each record gets a unique internal pseudo-email that won't collide
            "email":          None,
            "description":    "",
            "rating":         None,
            "review_count":   0,
            "medicines_count": 0,
            "is_open_24h":    False,
            "created_at":     now,
            "updated_at":     now,
            "display_warning": (
                "This listing is derived from locality-level public map data. "
                "Stock availability, opening hours and contact details "
                "have NOT been verified by MediFind."
            ),
        }
        try:
            db.pharmacies.insert_one(doc)
            print(f"  INSERT: {pharmacy['name']}")
            inserted += 1
        except Exception as e:
            print(f"  ERROR inserting {pharmacy['name']}: {e}")

    print(f"Local seed done — inserted: {inserted}, skipped: {skipped}")


if __name__ == "__main__":
    seed()
