"""
tests/conftest.py — Pytest fixtures shared across all tests.
"""

import pytest
from app import create_app


@pytest.fixture(scope="session")
def app():
    """Create a test Flask application."""
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    """A test client for the Flask app."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """A test runner for Flask CLI commands."""
    return app.test_cli_runner()


@pytest.fixture()
def auth_headers(client):
    """
    Register + login a test user and return JWT auth headers.
    Used by tests that require authentication.
    """
    client.post("/api/auth/register", json={
        "name":     "Test User",
        "email":    "testuser@example.com",
        "password": "Test@1234",
        "phone":    "9000000001",
        "role":     "USER",
    })
    resp = client.post("/api/auth/login", json={
        "email":    "testuser@example.com",
        "password": "Test@1234",
    })
    data = resp.get_json()
    token = data.get("data", {}).get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
