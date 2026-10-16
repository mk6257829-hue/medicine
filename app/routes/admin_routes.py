from flask import Blueprint
from app.utils import success_response
admin_bp = Blueprint('admin', __name__)
@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    return success_response('Admin routes � Phase 10.', status_code=200)

