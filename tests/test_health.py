"""tests/test_health.py — Smoke tests for application startup."""

def test_app_starts(client):
    """Homepage returns 200."""
    resp = client.get("/")
    assert resp.status_code == 200


def test_api_auth_register_missing_fields(client):
    """Register with empty body returns 400."""
    resp = client.post("/api/auth/register", json={})
    assert resp.status_code in (400, 422)


def test_api_medicines_returns_json(client):
    """Medicines endpoint returns JSON."""
    resp = client.get("/api/medicines/")
    assert resp.content_type.startswith("application/json")


def test_api_search_medicines(client):
    """Search endpoint responds."""
    resp = client.get("/api/search/medicines?q=para")
    assert resp.status_code == 200


def test_404_returns_json(client):
    """Unknown API route returns JSON 404."""
    resp = client.get("/api/nonexistent-route")
    assert resp.status_code == 404
