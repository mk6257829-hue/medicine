from flask import Blueprint
from app.utils import success_response
prescription_bp = Blueprint('prescriptions', __name__)
@prescription_bp.route('/', methods=['GET'])
def list_prescriptions():
    return success_response('Prescription routes � Phase 8.', status_code=200)

