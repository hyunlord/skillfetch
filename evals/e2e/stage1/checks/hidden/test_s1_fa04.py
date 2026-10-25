"""s1-fa-04: behaviour lock for GET/PUT/DELETE /items/{id} (passes on the baseline too)."""
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.hidden_s1.s1util import API, new_item, new_user, superuser_headers

METHODS = ["get", "put", "delete"]


def _call(client, method, item_id, headers):
    kw = {"json": {"title": "changed"}} if method == "put" else {}
    return getattr(client, method)(f"{API}/items/{item_id}", headers=headers, **kw)


@pytest.mark.parametrize("method", METHODS)
def test_missing_404(client: TestClient, method):
    u = new_user(client)
    r = _call(client, method, uuid.uuid4(), u["headers"])
    assert r.status_code == 404 and r.json()["detail"] == "Item not found"


@pytest.mark.parametrize("method", METHODS)
def test_other_users_item_403(client: TestClient, method):
    owner, other = new_user(client), new_user(client)
    item = new_item(client, owner["headers"])
    r = _call(client, method, item["id"], other["headers"])
    assert r.status_code == 403 and r.json()["detail"] == "Not enough permissions"


@pytest.mark.parametrize("method", METHODS)
def test_superuser_200(client: TestClient, method):
    owner = new_user(client)
    item = new_item(client, owner["headers"])
    assert _call(client, method, item["id"], superuser_headers(client)).status_code == 200


@pytest.mark.parametrize("method", METHODS)
def test_owner_200(client: TestClient, method):
    owner = new_user(client)
    item = new_item(client, owner["headers"])
    assert _call(client, method, item["id"], owner["headers"]).status_code == 200


def test_openapi_path_param_is_id(client: TestClient):
    paths = client.get(f"{API}/openapi.json").json()["paths"]
    ops = paths[f"{API}/items/{{id}}"]
    for method in METHODS:
        names = [p["name"] for p in ops[method].get("parameters", []) if p["in"] == "path"]
        assert names == ["id"], (method, names)
