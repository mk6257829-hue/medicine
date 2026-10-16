from flask import Blueprint
from app.utils import success_response
user_bp = Blueprint('users', __name__)
@user_bp.route('/', methods=['GET'])
def list_users():
    return success_response('User routes � Phase 2.', status_code=200)

