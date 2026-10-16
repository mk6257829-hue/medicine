"""
app/routes/main_routes.py — Public HTML page routes (Jinja2 templates).
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("about.html")


@main_bp.route("/contact")
def contact():
    return render_template("contact.html")


@main_bp.route("/medicines")
def medicines():
    return render_template("medicines.html")


@main_bp.route("/medicine/<medicine_id>")
def medicine_detail(medicine_id):
    return render_template("medicine_detail.html", medicine_id=medicine_id)


@main_bp.route("/pharmacies")
def pharmacies():
    return render_template("pharmacies.html")


@main_bp.route("/gangoh-map")
def gangoh_map():
    return render_template("gangoh_stores.html")


@main_bp.route("/pharmacy/<pharmacy_id>")
def pharmacy_detail(pharmacy_id):
    return render_template("pharmacy_detail.html", pharmacy_id=pharmacy_id)


@main_bp.route("/login")
def login():
    return render_template("auth/login.html")


@main_bp.route("/register")
def register():
    return render_template("auth/register.html")


# ── User pages ────────────────────────────────────────────────────────────────

@main_bp.route("/dashboard")
def user_dashboard():
    return render_template("user/dashboard.html")


@main_bp.route("/search")
def user_search():
    return render_template("user/search.html")


@main_bp.route("/availability")
def user_availability():
    return render_template("user/availability.html")


@main_bp.route("/prescriptions")
def user_prescriptions():
    return render_template("user/prescriptions.html")


@main_bp.route("/orders")
def user_orders():
    return render_template("user/orders.html")


@main_bp.route("/profile")
def user_profile():
    return render_template("user/profile.html")


@main_bp.route("/notifications")
def user_notifications():
    return render_template("user/notifications.html")


# ── Pharmacy pages ────────────────────────────────────────────────────────────

@main_bp.route("/pharmacy/dashboard")
def pharmacy_dashboard():
    return render_template("pharmacy/dashboard.html")


@main_bp.route("/pharmacy/profile")
def pharmacy_profile():
    return render_template("pharmacy/profile.html")


@main_bp.route("/pharmacy/inventory")
def pharmacy_inventory():
    return render_template("pharmacy/inventory.html")


@main_bp.route("/pharmacy/inventory/add")
def pharmacy_inventory_add():
    return render_template("pharmacy/inventory_add.html")


@main_bp.route("/pharmacy/orders")
def pharmacy_orders():
    return render_template("pharmacy/orders.html")


@main_bp.route("/pharmacy/prescriptions")
def pharmacy_prescriptions():
    return render_template("pharmacy/prescriptions.html")


@main_bp.route("/pharmacy/analytics")
def pharmacy_analytics():
    return render_template("pharmacy/analytics.html")


# ── Admin pages ───────────────────────────────────────────────────────────────

@main_bp.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html")


@main_bp.route("/admin/users")
def admin_users():
    return render_template("admin/users.html")


@main_bp.route("/admin/pharmacies")
def admin_pharmacies():
    return render_template("admin/pharmacies.html")


@main_bp.route("/admin/medical-stores")
def admin_medical_stores():
    return render_template("admin/medical_stores.html")


@main_bp.route("/admin/medicines")
def admin_medicines():
    return render_template("admin/medicines.html")


@main_bp.route("/admin/inventory")
def admin_inventory():
    return render_template("admin/inventory.html")


@main_bp.route("/admin/orders")
def admin_orders():
    return render_template("admin/orders.html")


@main_bp.route("/admin/prescriptions")
def admin_prescriptions():
    return render_template("admin/prescriptions.html")


@main_bp.route("/admin/reports")
def admin_reports():
    return render_template("admin/reports.html")


@main_bp.route("/admin/audit-logs")
def admin_audit_logs():
    return render_template("admin/audit_logs.html")

