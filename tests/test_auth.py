from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_and_login():
    resp = client.post("/auth/register", json={"email": "a@example.com", "password": "pass1234"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    resp2 = client.post("/auth/login", json={"email": "a@example.com", "password": "pass1234"})
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()


def test_login_wrong_password():
    client.post("/auth/register", json={"email": "b@example.com", "password": "pass1234"})
    resp = client.post("/auth/login", json={"email": "b@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_is_case_insensitive_for_existing_email():
    # A previously registered account remains accessible regardless of email casing.
    client.post("/auth/register", json={"email": "CaseUser@example.com", "password": "pass1234"})
    response = client.post("/auth/login", json={"email": "caseuser@EXAMPLE.com", "password": "pass1234"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_registration_rejects_duplicate_email_with_different_case():
    client.post("/auth/register", json={"email": "Duplicate@example.com", "password": "pass1234"})
    response = client.post("/auth/register", json={"email": "duplicate@EXAMPLE.com", "password": "pass1234"})
    assert response.status_code == 400


def test_login_rejects_wrong_password_after_email_normalization():
    client.post("/auth/register", json={"email": "secure@example.com", "password": "pass1234"})
    response = client.post("/auth/login", json={"email": "SECURE@example.com", "password": "wrong-password"})
    assert response.status_code == 401
