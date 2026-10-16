from flask import Blueprint
from app.utils import success_response
order_bp = Blueprint('orders', __name__)
@order_bp.route('/', methods=['GET'])
def list_orders():
    return success_response('Order routes � Phase 9.', status_code=200)

