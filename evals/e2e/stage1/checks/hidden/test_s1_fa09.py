"""s1-fa-09: e-mail addresses are case-insensitive."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from tests.hidden_s1.s1util import API, new_user, rand, superuser_headers


def test_signup_case_variant_400(client: TestClient):
    email = f"{rand()}@example.com"
    r = client.post(f"{API}/users/signup", json={"email": email, "password": rand()})
    assert r.status_code == 200, r.text
    r = client.post(f"{API}/users/signup", json={"email": email.upper(), "password": rand()})
    assert r.status_code == 400, r.text


def test_login_upper_superuser_200(client: TestClient):
    r = client.post(f"{API}/login/access-token", data={
        "username": settings.FIRST_SUPERUSER.upper(), "password": settings.FIRST_SUPERUSER_PASSWORD})
    assert r.status_code == 200, r.text


def test_superuser_create_case_variant_400(client: TestClient):
    existing = new_user(client)
    with patch.object(settings, "SMTP_HOST", None):  # no e-mail on create
        r = client.post(f"{API}/users/", headers=superuser_headers(client),
                        json={"email": existing["email"].upper(), "password": rand()})
    assert r.status_code == 400, r.text


def test_patch_me_case_variant_409(client: TestClient):
    other, me = new_user(client), new_user(client)
    r = client.patch(f"{API}/users/me", headers=me["headers"], json={"email": other["email"].upper()})
    assert r.status_code == 409, r.text
