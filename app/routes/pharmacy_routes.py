"""
app/routes/pharmacy_routes.py — Pharmacy API routes.

Endpoints:
  GET  /api/pharmacies/             — List pharmacies (with optional filters)
  GET  /api/pharmacies/map          — Map-ready list (city=Gangoh, etc.)
  GET  /api/pharmacies/nearby       — Geo-search by lat/lng/radius
  GET  /api/pharmacies/search       — Search by name
  GET  /api/pharmacies/<id>         — Single pharmacy detail
  POST /api/pharmacies/import-osm   — Import OSM records (admin only)
"""

import logging
import math
import re
from datetime import datetime, timezone
from flask import Blueprint, request
from bson import ObjectId
from pymongo import GEOSPHERE

from app.utils import success_response, error_response, object_id_to_str
from app.database import DatabaseUnavailableError

logger = logging.getLogger(__name__)

pharmacy_bp = Blueprint("pharmacies", __name__)

# ── Helper ─────────────────────────────────────────────────────────────────────

def _get_db_safe():
    """Return DB handle or raise DatabaseUnavailableError."""
    from app.database import get_db
    return get_db()


def _serialise(pharmacy: dict) -> dict:
    """Convert ObjectId/datetime and ensure safe JSON output."""
    p = object_id_to_str(pharmacy)
    # Flatten GeoJSON location for frontend convenience
    if isinstance(p.get("location"), dict) and p["location"].get("type") == "Point":
        coords = p["location"].get("coordinates", [])
        if len(coords) == 2:
            p["longitude"] = coords[0]
            p["latitude"]  = coords[1]
    return p


# ── List / Map Endpoint ────────────────────────────────────────────────────────

@pharmacy_bp.route("/", methods=["GET"])
@pharmacy_bp.route("/map", methods=["GET"])
def list_pharmacies():
    """
    Return pharmacies, optionally filtered.

    Query params:
      city      — case-insensitive city name (e.g. Gangoh)
      q         — name substring search
      verified  — 'true' | 'false'
      active    — 'true' | 'false'
      limit     — max records (default 100)
      page      — page number (default 1)
    """
    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        return error_response(
            "Database unavailable — please ensure MongoDB is running.",
            "DB_UNAVAILABLE", 503
        )

    city     = request.args.get("city", "").strip()
    q        = request.args.get("q", "").strip()
    verified = request.args.get("verified", "")
    active   = request.args.get("active", "")
    try:
        limit = min(int(request.args.get("limit", 100)), 200)
        page  = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        limit, page = 100, 1

    filt = {}
    if city:
        import re
        filt["city"] = re.compile(re.escape(city), re.IGNORECASE)
    if q:
        import re
        filt["name"] = re.compile(re.escape(q), re.IGNORECASE)
    if verified == "true":
        filt["verification_status"] = "VERIFIED"
    if active == "false":
        filt["is_active"] = False
    elif active != "":
        filt["is_active"] = True

    skip = (page - 1) * limit
    total = db.pharmacies.count_documents(filt)
    pharmacies = list(db.pharmacies.find(filt).skip(skip).limit(limit))

    return success_response(
        f"{len(pharmacies)} pharmacies found.",
        data={
            "pharmacies": [_serialise(p) for p in pharmacies],
            "total": total,
            "page": page,
            "limit": limit,
        }
    )


# ── Nearby Search ──────────────────────────────────────────────────────────────

@pharmacy_bp.route("/nearby", methods=["GET"])
def nearby_pharmacies():
    """
    Return pharmacies near a geographic point.

    Query params:
      lat    — latitude  (required)
      lng    — longitude (required)
      radius — search radius in metres (default 5000)
      limit  — max results (default 20)
    """
    try:
        lat    = float(request.args.get("lat", ""))
        lng    = float(request.args.get("lng", ""))
    except (TypeError, ValueError):
        return error_response("lat and lng query parameters are required and must be numbers.", "VALIDATION_ERROR", 400)

    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        return error_response("lat must be between -90 and 90; lng between -180 and 180.", "VALIDATION_ERROR", 400)

    try:
        radius = min(int(request.args.get("radius", 5000)), 50000)
        limit  = min(int(request.args.get("limit", 20)), 100)
    except (TypeError, ValueError):
        radius, limit = 5000, 20

    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        db = None

    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [lng, lat]},
                "distanceField": "distance_metres",
                "maxDistance": radius,
                "spherical": True,
            }
        },
        {"$limit": limit},
    ]

    pharmacies = []
    try:
        if db is not None:
            pharmacies = list(db.pharmacies.aggregate(pipeline))
    except Exception as exc:
        logger.warning("geoNear failed (index may be missing): %s", exc)
        # Fallback: return all with manual distance calculation
        all_ph = list(db.pharmacies.find({}).limit(200)) if db is not None else []
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlam = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        for p in all_ph:
            coords = (p.get("location") or {}).get("coordinates", [])
            if len(coords) == 2:
                p["distance_metres"] = haversine(lat, lng, coords[1], coords[0])
            else:
                p["distance_metres"] = float("inf")

        pharmacies = sorted(
            [p for p in all_ph if p["distance_metres"] <= radius],
            key=lambda x: x["distance_metres"]
        )[:limit]

    results = [_serialise(p) for p in pharmacies]
    # Query the configured external provider as well as registered stores. The key
    # remains on the server and external results stay explicitly unverified.
    from flask import current_app
    if current_app.config.get("MAP_API_PROVIDER") == "google" and current_app.config.get("MAP_API_KEY"):
        try:
            import json
            import urllib.parse
            import urllib.request
            params = urllib.parse.urlencode({"location": f"{lat},{lng}", "radius": radius, "type": "pharmacy", "key": current_app.config["MAP_API_KEY"]})
            req = urllib.request.Request(f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?{params}", headers={"User-Agent": "MedicineAvailability/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                places = json.loads(response.read().decode("utf-8"))
            for place in places.get("results", []):
                loc = place.get("geometry", {}).get("location", {})
                if "lat" not in loc or "lng" not in loc:
                    continue
                results.append({"_id": "google-" + str(place.get("place_id", "")), "name": place.get("name", "Medical store"), "address": place.get("vicinity", ""), "latitude": loc["lat"], "longitude": loc["lng"], "verification_status": "UNVERIFIED", "source": "google_places", "display_warning": "Externally sourced map listing. Details and stock have not been verified."})
        except Exception as exc:
            logger.info("Google Places lookup unavailable: %s", exc)

    return success_response(
        f"{len(results)} medical stores found within {radius}m.",
        data={"pharmacies": results, "source": "registered" if pharmacies else ("google_places" if results else "none")}
    )


@pharmacy_bp.route("/", methods=["POST"])
def register_medical_store():
    """Accept a community-submitted listing as unverified; never imply stock availability."""
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    address = str(data.get("address", "")).strip()
    phone = str(data.get("phone", "")).strip()
    if not name or len(name) > 120 or not address or len(address) > 300:
        return error_response("Store name (1–120 chars) and address (1–300 chars) are required.", "VALIDATION_ERROR", 400)
    if phone and not re.fullmatch(r"\+?[\d\s()\-]{7,20}", phone):
        return error_response("Enter a valid phone number.", "VALIDATION_ERROR", 400)
    try:
        lat, lng = float(data.get("latitude")), float(data.get("longitude"))
    except (TypeError, ValueError):
        return error_response("Latitude and longitude must be numbers.", "VALIDATION_ERROR", 400)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return error_response("Latitude or longitude is out of range.", "VALIDATION_ERROR", 400)
    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        return error_response("Database unavailable.", "DB_UNAVAILABLE", 503)
    duplicate = db.pharmacies.find_one({"name": re.compile(r"^" + re.escape(name) + r"$", re.I), "address": re.compile(r"^" + re.escape(address) + r"$", re.I)})
    if duplicate:
        return error_response("This store is already listed.", "DUPLICATE_STORE", 409)
    store = {"name": name, "address": address, "phone": phone or None, "city": "Gangoh", "state": "Uttar Pradesh", "location": {"type": "Point", "coordinates": [lng, lat]}, "latitude": lat, "longitude": lng, "verification_status": "UNVERIFIED", "listing_status": "COMMUNITY_SUBMITTED", "source": "community_submission", "is_active": True, "created_at": datetime.now(timezone.utc)}
    result = db.pharmacies.insert_one(store)
    store["_id"] = result.inserted_id
    return success_response("Store submitted for review. It is listed as unverified.", {"pharmacy": _serialise(store)}, 201)


# ── Name Search ────────────────────────────────────────────────────────────────

@pharmacy_bp.route("/search", methods=["GET"])
def search_pharmacies():
    """Search pharmacies by name or address."""
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return error_response("q must be at least 2 characters.", "VALIDATION_ERROR", 400)

    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        return error_response("Database unavailable.", "DB_UNAVAILABLE", 503)

    import re
    pattern = re.compile(re.escape(q), re.IGNORECASE)
    results = list(db.pharmacies.find({
        "$or": [{"name": pattern}, {"address": pattern}, {"city": pattern}]
    }).limit(50))

    return success_response(
        f"{len(results)} pharmacies found.",
        data={"pharmacies": [_serialise(p) for p in results]}
    )


# ── Single Pharmacy ────────────────────────────────────────────────────────────

@pharmacy_bp.route("/<pharmacy_id>", methods=["GET"])
def get_pharmacy(pharmacy_id):
    """Return a single pharmacy by ObjectId or by string slug."""
    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        return error_response("Database unavailable.", "DB_UNAVAILABLE", 503)

    pharmacy = None
    try:
        pharmacy = db.pharmacies.find_one({"_id": ObjectId(pharmacy_id)})
    except Exception:
        pass

    if not pharmacy:
        return error_response("Pharmacy not found.", "NOT_FOUND", 404)

    return success_response("Pharmacy retrieved.", data={"pharmacy": _serialise(pharmacy)})


# ── OSM Live Fetch ─────────────────────────────────────────────────────────────

@pharmacy_bp.route("/osm-fetch", methods=["GET"])
def osm_fetch():
    """
    Fetch pharmacies/chemists for a bounding box from Overpass API (read-only).
    Returns OSM results merged with our DB records for display on the map.

    Query params:
      south, west, north, east — bounding box (defaults to Gangoh area)
      save   — if 'true', save new records to DB (not implemented yet)
    """
    try:
        south = float(request.args.get("south", 29.74))
        west  = float(request.args.get("west",  77.27))
        north = float(request.args.get("north", 29.82))
        east  = float(request.args.get("east",  77.35))
    except (TypeError, ValueError):
        return error_response("Invalid bounding box parameters.", "VALIDATION_ERROR", 400)

    import urllib.request
    import urllib.parse
    import urllib.error
    import json as json_mod

    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
[out:json][timeout:20];
(
  node["amenity"="pharmacy"]({south},{west},{north},{east});
  node["shop"="chemist"]({south},{west},{north},{east});
  way["amenity"="pharmacy"]({south},{west},{north},{east});
);
out center tags;
"""
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(
        overpass_url, data=data,
        headers={"User-Agent": "MediFind/1.0 (medicine availability app)"},
    )

    osm_results = []
    osm_error   = None
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
            osm_data = json_mod.loads(raw)
            for el in osm_data.get("elements", []):
                tags = el.get("tags", {})
                if el["type"] == "node":
                    lat, lng = el.get("lat"), el.get("lon")
                elif el["type"] == "way":
                    c = el.get("center", {})
                    lat, lng = c.get("lat"), c.get("lon")
                else:
                    continue
                if lat is None or lng is None:
                    continue
                name = tags.get("name") or tags.get("name:en") or "Medical Store"
                osm_results.append({
                    "osm_id":   str(el["id"]),
                    "osm_type": el["type"],
                    "name":     name,
                    "address":  tags.get("addr:full") or tags.get("addr:street") or "Gangoh",
                    "city":     tags.get("addr:city") or "Gangoh",
                    "state":    "Uttar Pradesh",
                    "pincode":  tags.get("addr:postcode") or "247341",
                    "phone":    tags.get("phone") or tags.get("contact:phone"),
                    "latitude":  lat,
                    "longitude": lng,
                    "location":  {"type": "Point", "coordinates": [lng, lat]},
                    "verification_status": "UNVERIFIED",
                    "source":    "osm_overpass_live",
                    "display_warning": (
                        "This listing is from OpenStreetMap (live fetch). "
                        "Accuracy not guaranteed."
                    ),
                })
    except urllib.error.HTTPError as e:
        osm_error = f"Overpass API error: HTTP {e.code}"
        logger.warning("OSM Overpass error: %s", e)
    except urllib.error.URLError as e:
        osm_error = f"Could not reach Overpass API: {e.reason}"
        logger.warning("OSM Overpass unreachable: %s", e)
    except Exception as e:
        osm_error = f"Unexpected error: {e}"
        logger.exception("OSM fetch error")

    return success_response(
        f"{len(osm_results)} OSM pharmacies fetched." if not osm_error else osm_error,
        data={
            "pharmacies": osm_results,
            "osm_count":  len(osm_results),
            "osm_error":  osm_error,
        }
    )


# ── Stats Summary ──────────────────────────────────────────────────────────────

@pharmacy_bp.route("/stats", methods=["GET"])
def pharmacy_stats():
    """Return summary counts for the pharmacies collection."""
    try:
        db = _get_db_safe()
    except DatabaseUnavailableError:
        return error_response("Database unavailable.", "DB_UNAVAILABLE", 503)

    total    = db.pharmacies.count_documents({})
    verified = db.pharmacies.count_documents({"verification_status": "VERIFIED"})
    gangoh   = db.pharmacies.count_documents({"city": {"$regex": "Gangoh", "$options": "i"}})

    return success_response(
        "Stats retrieved.",
        data={"total": total, "verified": verified, "gangoh": gangoh}
    )
