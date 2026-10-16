"""Public Gangoh medical-store directory and admin CRUD API."""

from datetime import datetime, timezone
import re

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.middleware.auth_middleware import require_admin
from app.models.medical_store import GANGOH_BOUNDS, normalize_store, serialize_store

medical_store_bp = Blueprint("medical_stores", __name__)


def _within_gangoh():
    b = GANGOH_BOUNDS
    return {"$or": [
        {"latitude": None},
        {"latitude": {"$gte": b["south"], "$lte": b["north"]},
         "longitude": {"$gte": b["west"], "$lte": b["east"]}},
    ]}


@medical_store_bp.get("/")
def list_stores():
    query = dict(_within_gangoh())
    query["$and"] = [{"city": "Gangoh"}, {"state": "Uttar Pradesh"}]
    term = request.args.get("q", "").strip()
    if term:
        escaped = re.escape(term)
        query["$and"].append({"$or": [{"name": {"$regex": escaped, "$options": "i"}},
                                        {"address": {"$regex": escaped, "$options": "i"}}]})
    docs = [serialize_store(d) for d in get_db().medical_stores.find(query).sort("name", 1).limit(500)]
    return jsonify({"success": True, "data": {"stores": docs, "count": len(docs)}})


@medical_store_bp.post("/")
@require_admin
def create_store():
    try:
        doc = normalize_store(request.get_json(silent=True) or {})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    now = datetime.now(timezone.utc)
    doc["created_at"] = now
    try:
        result = get_db().medical_stores.insert_one(doc)
    except DuplicateKeyError:
        return jsonify({"success": False, "message": "A store with the same name and address or source identity already exists."}), 409
    doc["_id"] = result.inserted_id
    return jsonify({"success": True, "message": "Store added.", "data": {"store": serialize_store(doc)}}), 201


@medical_store_bp.route("/<store_id>", methods=["PUT", "PATCH"])
@require_admin
def update_store(store_id):
    try:
        oid = ObjectId(store_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid store ID."}), 400
    collection = get_db().medical_stores
    current = collection.find_one({"_id": oid})
    if not current:
        return jsonify({"success": False, "message": "Store not found."}), 404
    try:
        doc = normalize_store(request.get_json(silent=True) or {}, current)
        collection.update_one({"_id": oid}, {"$set": doc})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except DuplicateKeyError:
        return jsonify({"success": False, "message": "Another store with the same name and address already exists."}), 409
    return jsonify({"success": True, "message": "Store updated.", "data": {"store": serialize_store(collection.find_one({"_id": oid}))}})


@medical_store_bp.delete("/<store_id>")
@require_admin
def delete_store(store_id):
    try:
        oid = ObjectId(store_id)
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid store ID."}), 400
    result = get_db().medical_stores.delete_one({"_id": oid})
    if not result.deleted_count:
        return jsonify({"success": False, "message": "Store not found."}), 404
    return jsonify({"success": True, "message": "Store deleted."})
