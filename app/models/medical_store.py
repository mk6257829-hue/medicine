"""MongoDB document helpers and validation for the Gangoh directory."""

from datetime import datetime, timezone

from bson import ObjectId

# Town bounds are deliberately tight: remote Saharanpur city coordinates cannot
# enter through either public search or the admin write API.
GANGOH_BOUNDS = {"south": 29.74, "north": 29.82, "west": 77.27, "east": 77.35}


def normalize_store(payload, existing=None):
    existing = existing or {}
    name = str(payload.get("name", existing.get("name", ""))).strip()
    address = str(payload.get("address", existing.get("address", ""))).strip()
    if not name or not address:
        raise ValueError("Store name and address are required.")

    identity = " ".join(f"{name} {address}".casefold().split())
    doc = {"name": name, "address": address, "dedupe_key": identity, "city": "Gangoh", "district": "Saharanpur",
           "state": "Uttar Pradesh", "source": str(payload.get("source", existing.get("source", "admin"))).strip() or "admin",
           "source_id": str(payload.get("source_id", existing.get("source_id", ""))).strip() or None,
           "phone": str(payload.get("phone", existing.get("phone") or "")).strip() or None,
           "opening_hours": str(payload.get("opening_hours", existing.get("opening_hours") or "")).strip() or None,
           "verified": payload.get("verified", existing.get("verified", False)) in (True, "true", "1", 1),
           "updated_at": datetime.now(timezone.utc)}

    for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        raw = payload.get(field, existing.get(field))
        if raw in (None, ""):
            doc[field] = None
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{field.title()} must be a valid number.")
        if not low <= value <= high:
            raise ValueError(f"{field.title()} is out of range.")
        doc[field] = value

    lat, lng = doc["latitude"], doc["longitude"]
    if (lat is None) != (lng is None):
        raise ValueError("Provide both coordinates, or leave both blank.")
    if lat is not None and not (GANGOH_BOUNDS["south"] <= lat <= GANGOH_BOUNDS["north"] and GANGOH_BOUNDS["west"] <= lng <= GANGOH_BOUNDS["east"]):
        raise ValueError("Coordinates must be within the Gangoh town directory area.")
    return doc


def serialize_store(doc):
    result = dict(doc)
    result["_id"] = str(result["_id"]) if isinstance(result.get("_id"), ObjectId) else result.get("_id")
    for field in ("created_at", "updated_at"):
        if result.get(field):
            result[field] = result[field].isoformat()
    return result
