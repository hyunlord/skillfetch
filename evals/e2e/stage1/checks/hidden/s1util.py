"""Helpers for the stage-1 hidden tests (copied next to them into backend/tests/hidden_s1/)."""
import random
import string

from fastapi.testclient import TestClient

from app.core.config import settings

API = settings.API_V1_STR


def rand(k: int = 16) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=k))


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    r = client.post(f"{API}/login/access-token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def superuser_headers(client: TestClient) -> dict[str, str]:
    return login(client, settings.FIRST_SUPERUSER, settings.FIRST_SUPERUSER_PASSWORD)


def new_user(client: TestClient, email: str | None = None) -> dict:
    """Sign up a fresh user through the public API and log in."""
    email = email or f"{rand()}@example.com"
    password = rand()
    r = client.post(f"{API}/users/signup", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"id": r.json()["id"], "email": email, "password": password,
            "headers": login(client, email, password)}


def new_item(client: TestClient, headers: dict[str, str], **body) -> dict:
    body.setdefault("title", rand())
    r = client.post(f"{API}/items/", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()
