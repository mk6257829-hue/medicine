from flask import Blueprint
from app.utils import success_response
inventory_bp = Blueprint('inventory', __name__)
@inventory_bp.route('/', methods=['GET'])
def list_inventory():
    return success_response('Inventory routes � Phase 5.', status_code=200)

