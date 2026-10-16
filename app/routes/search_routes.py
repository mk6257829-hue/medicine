from flask import Blueprint
from app.utils import success_response
search_bp = Blueprint('search', __name__)
@search_bp.route('/medicines', methods=['GET'])
def search_medicines():
    return success_response('Search routes � Phase 3.', status_code=200)

