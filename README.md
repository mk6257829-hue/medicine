<<<<<<< HEAD
# MediFind — Medicine Availability & Pharmacy Network

> A production-ready full-stack web platform connecting patients with nearby pharmacies through real-time medicine availability, inventory management, and seamless reservations.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔍 Medicine Search | Partial match, text search, category filter |
| 🏥 Pharmacy Directory | Verified pharmacies with geolocation |
| 📍 Nearby Search | GPS/pincode-based pharmacy finder |
| 📦 Inventory Management | Stock, batch, expiry, price management |
| 📄 Prescription Upload | Secure PDF/image upload with review flow |
| 🛒 Order/Reservation | Reserve medicines from pharmacies |
| 🔐 Role-Based Access | USER / PHARMACY_OWNER / PHARMACIST / ADMIN |
| 📊 Admin Dashboard | Analytics, audit logs, user management |
| 🔔 Notifications | In-app notification system |

---

## 🏗 Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3, Flask, Flask-JWT-Extended, Flask-CORS, Flask-Limiter |
| **Database** | MongoDB (PyMongo), 2dsphere geospatial index |
| **Frontend** | HTML5, CSS3, Tailwind CSS, Bootstrap 5, Vanilla JS ES6+ |
| **Auth** | JWT (Bearer token + httpOnly cookie) |
| **Security** | Werkzeug password hashing, rate limiting, input validation |
| **Testing** | Pytest, pytest-flask |

---

## 📁 Folder Structure

```
medicine/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── database/
│   │   └── connection.py    # MongoDB singleton + indexes
│   ├── routes/              # Flask Blueprints (one per module)
│   ├── services/            # Business logic
│   ├── utils/               # Helpers (response, validation, pagination)
│   └── middleware/          # Auth decorators (RBAC)
├── templates/               # Jinja2 HTML templates
│   ├── base.html            # Master layout
│   ├── index.html           # Homepage
│   ├── auth/                # Login, Register
│   ├── user/                # User dashboard pages
│   ├── pharmacy/            # Pharmacy dashboard pages
│   └── admin/               # Admin dashboard pages
├── static/
│   ├── css/main.css         # Design system
│   └── js/                  # api.js, auth.js, ui.js, main.js
├── tests/                   # Pytest test suite
├── config.py                # Config classes (dev/test/prod)
├── run.py                   # Entry point
├── requirements.txt
├── .env                     # Local secrets (never commit)
└── .env.example             # Template for .env
```

---

## 🚀 Installation & Setup

### 1. Prerequisites

- Python 3.10+
- MongoDB 6.0+ (running locally or Atlas URI)
- Node.js not required (Tailwind loaded via CDN)

### 2. Clone & Enter Directory

```bash
git clone <repo-url>
cd medicine
```

### 3. Create & Activate Virtual Environment

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your values
```

Required `.env` variables:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask secret key | (must change) |
| `JWT_SECRET_KEY` | JWT signing key | (must change) |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/medicine_platform` |
| `UPLOAD_FOLDER` | Prescription upload path | `static/uploads` |
| `MAX_FILE_SIZE` | Upload size limit (bytes) | `5242880` (5 MB) |

### 6. Start MongoDB

```bash
# Local MongoDB
mongod --dbpath /data/db

# Or use MongoDB Atlas — just set MONGO_URI in .env
```

### 7. Run Flask (Development)

```bash
python run.py
```

App will be at: **http://localhost:5000**

---

## 🌱 Seed Database

### Gangoh medical-store directory

The permanent directory uses the separate MongoDB `medical_stores` collection. Public search is available at `/gangoh-map` and `/api/medical-stores/?q=...`; records are strictly scoped to Gangoh, Saharanpur. Admins can manage entries at `/admin/medical-stores` (API writes require an `ADMIN` JWT).

Run the idempotent directory seed with:

```bash
python scripts/seed_medical_stores.py
```

The initial store list was not present when this directory was implemented, so the seed dataset is intentionally empty. Add only source-backed records to `INITIAL_STORES` with stable `source` and `source_id` values. Unknown phone numbers, coordinates, and opening hours must remain blank. The admin form restricts supplied coordinates to Gangoh town bounds and exposes a separate confirmation flag.

After completing Phase 2, run the seed script:

```bash
python -m app.database.seed
```

This creates:
- 1 Admin user
- 10 regular users
- 5 pharmacies (pre-verified)
- 30 medicines (various categories)
- Inventory records
- Sample orders and prescriptions

---

## 🔌 API Documentation

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new user |
| `POST` | `/api/auth/login` | Login, receive JWT |
| `POST` | `/api/auth/logout` | Invalidate session |
| `GET`  | `/api/auth/me` | Get current user |

### Medicines

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/medicines/` | List medicines (paginated) |
| `GET`  | `/api/medicines/<id>` | Get medicine detail |
| `POST` | `/api/medicines/` | Create medicine (Admin) |
| `PUT`  | `/api/medicines/<id>` | Update medicine (Admin) |

### Search

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/search/medicines?q=para` | Full-text medicine search |
| `GET`  | `/api/search/availability/<med_id>` | Pharmacy availability for medicine |

### Pharmacies

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/pharmacies/` | List verified pharmacies |
| `GET`  | `/api/pharmacies/<id>` | Pharmacy detail |
| `POST` | `/api/pharmacies/` | Register pharmacy |
| `GET`  | `/api/pharmacies/nearby?lat=&lng=&radius=` | Nearby pharmacies (km) |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/inventory/` | List inventory (pharmacy staff) |
| `POST` | `/api/inventory/` | Add inventory item |
| `PUT`  | `/api/inventory/<id>` | Update stock/price/batch |
| `DELETE`| `/api/inventory/<id>` | Deactivate inventory |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/orders/` | List user orders |
| `POST` | `/api/orders/` | Create order |
| `GET`  | `/api/orders/<id>` | Order detail |
| `PUT`  | `/api/orders/<id>/status` | Update order status |

### Prescriptions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/prescriptions/` | Upload prescription |
| `GET`  | `/api/prescriptions/` | List prescriptions |
| `PUT`  | `/api/prescriptions/<id>/status` | Review prescription |

### Admin

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/api/admin/dashboard` | Dashboard stats |
| `GET`  | `/api/admin/users` | All users |
| `GET`  | `/api/admin/pharmacies` | All pharmacies |
| `PUT`  | `/api/admin/pharmacies/<id>/verify` | Verify/reject pharmacy |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## 📦 Production Deployment

### Using Gunicorn

```bash
gunicorn "app:create_app('production')" \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Environment Variables for Production

```
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
MONGO_URI=<mongodb-atlas-uri>
```

---

## 🔐 Security Notes

- Passwords hashed with Werkzeug's `generate_password_hash` (PBKDF2 SHA-256)
- JWT stored as httpOnly cookie (CSRF protected) + Bearer header
- File uploads validated by extension + MIME type + size limit
- Rate limiting on auth endpoints (Flask-Limiter)
- MongoDB queries sanitised — no raw string interpolation
- All secrets via environment variables — never hardcoded

---

## 📋 Implementation Phases

| Phase | Status | Description |
|---|---|---|
| Phase 1 | ✅ Complete | Project setup, base templates, design system |
| Phase 2 | 🔄 Next | Authentication, registration, RBAC |
| Phase 3 | ⏳ Pending | Medicine CRUD & search |
| Phase 4 | ⏳ Pending | Pharmacy management |
| Phase 5 | ⏳ Pending | Inventory management |
| Phase 6 | ⏳ Pending | Geospatial nearby search |
| Phase 7 | ⏳ Pending | User dashboard & availability |
| Phase 8 | ⏳ Pending | Prescription module |
| Phase 9 | ⏳ Pending | Order/reservation system |
| Phase 10 | ⏳ Pending | Admin dashboard & analytics |
| Phase 11 | ⏳ Pending | Security hardening & testing |
| Phase 12 | ⏳ Pending | Deployment documentation |

---

## 👥 User Roles

| Role | Access |
|---|---|
| `USER` | Search, view, order, upload prescriptions |
| `PHARMACY_OWNER` | Manage pharmacy, inventory, orders |
| `PHARMACIST` | Manage inventory, review prescriptions |
| `ADMIN` | Full platform access |

---

*MediFind — Connecting Patients with Pharmacies*
=======
# medicine
>>>>>>> 6bf332fc7719001e30a62631aa9ddb6ab223be39
