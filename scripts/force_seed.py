"""
Force-fix: drop ALL email indexes on pharmacies collection and recreate as non-unique sparse.
Then seed all 7 Gangoh pharmacies directly using insert_many (bypassing session retries).
"""
import sys, os, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from dotenv import load_dotenv
load_dotenv()
from app import create_app

app = create_app("development")
with app.app_context():
    from app.database import get_db, DatabaseUnavailableError
    from pymongo import ASCENDING
    from datetime import datetime, timezone
    from pymongo.errors import DuplicateKeyError

    try:
        db = get_db()
    except DatabaseUnavailableError as e:
        print(f"ERROR: {e}"); sys.exit(1)

    # 1. Show all current indexes
    print("Current pharmacy indexes:")
    for name, info in db.pharmacies.index_information().items():
        print(f"  {name}: {info}")

    # 2. Drop ALL email-related indexes
    for name, info in list(db.pharmacies.index_information().items()):
        keys = [k for k, _ in info.get("key", [])]
        if "email" in keys:
            print(f"Dropping index '{name}'...")
            db.pharmacies.drop_index(name)

    # 3. Recreate as non-unique sparse
    db.pharmacies.create_index(
        [("email", ASCENDING)],
        sparse=True,
        name="pharmacies_email_sparse",
    )
    print("Recreated pharmacies_email_sparse (non-unique, sparse). Done.")

    # 4. Seed pharmacies using insert_many (no session, no retries)
    now = datetime.now(timezone.utc)
    PHARMACIES = [
        {"name": "Shri Ram Medical Store", "address": "Near Bus Stand, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3083, 29.7833]}},
        {"name": "Jan Aushadhi Kendra Gangoh", "address": "Main Market, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3090, 29.7840]}},
        {"name": "Agarwal Medical Store", "address": "Sadar Bazaar, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3075, 29.7828]}},
        {"name": "City Medical Hall", "address": "Court Road, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3068, 29.7845]}},
        {"name": "Sharma Drug House", "address": "Civil Hospital Road, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3095, 29.7820]}},
        {"name": "Gupta Medical Agency", "address": "Anaj Mandi Road, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3100, 29.7850]}},
        {"name": "New Life Pharmacy", "address": "Thana Road, Gangoh",
         "location": {"type": "Point", "coordinates": [77.3060, 29.7838]}},
    ]

    inserted = 0
    skipped = 0
    for ph in PHARMACIES:
        existing = db.pharmacies.find_one({"name": ph["name"], "city": "Gangoh"})
        if existing:
            print(f"  SKIP (exists): {ph['name']}")
            skipped += 1
            continue
        doc = {
            **ph,
            "city": "Gangoh",
            "state": "Uttar Pradesh",
            "pincode": "247341",
            "phone": None,
            "email": None,
            "owner_id": None,
            "verification_status": "UNVERIFIED",
            "is_active": True,
            "source": "local_estimate",
            "description": "",
            "rating": None,
            "review_count": 0,
            "medicines_count": 0,
            "is_open_24h": False,
            "created_at": now,
            "updated_at": now,
            "display_warning": (
                "This listing is derived from locality-level public map data. "
                "Stock availability, opening hours and contact details "
                "have NOT been verified by MediFind."
            ),
        }
        try:
            db.pharmacies.insert_one(doc, bypass_document_validation=False)
            print(f"  INSERT: {ph['name']}")
            inserted += 1
        except DuplicateKeyError as e:
            print(f"  DUP KEY ERROR for {ph['name']}: {e}")
        except Exception as e:
            print(f"  ERROR for {ph['name']}: {e}")

    print(f"\nDone — inserted: {inserted}, skipped: {skipped}")
    total = db.pharmacies.count_documents({"city": re.compile("Gangoh", re.IGNORECASE)})
    print(f"Total Gangoh pharmacies in DB: {total}")
