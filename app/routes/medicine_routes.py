from flask import Blueprint
from app.utils import success_response
medicine_bp = Blueprint('medicines', __name__)
@medicine_bp.route('/', methods=['GET'])
def list_medicines():
    return success_response('Medicine routes � Phase 3.', status_code=200)

