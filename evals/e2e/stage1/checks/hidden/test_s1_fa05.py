"""s1-fa-05: skip/limit on GET /items/ and GET /users/ keep their contract."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.models import Item, User
from tests.hidden_s1.s1util import API, new_item, new_user, superuser_headers


@pytest.mark.parametrize("path", ["/items/", "/users/"])
def test_openapi_skip_limit(client: TestClient, path):
    op = client.get(f"{API}/openapi.json").json()["paths"][f"{API}{path}"]["get"]
    params = {p["name"]: p for p in op.get("parameters", []) if p["in"] == "query"}
    for name, default in (("skip", 0), ("limit", 100)):
        assert name in params, (path, sorted(params))
        schema = params[name].get("schema", {})
        assert schema.get("type") == "integer", (path, name, schema)
        assert schema.get("default", params[name].get("default")) == default, (path, name, schema)


@pytest.mark.parametrize("path,model", [("/items/", Item), ("/users/", User)])
def test_skip1_limit1(client: TestClient, db: Session, path, model):
    su = superuser_headers(client)
    for _ in range(2):
        new_item(client, new_user(client)["headers"])
    total = db.exec(select(func.count()).select_from(model)).one()
    assert total >= 2
    r = client.get(f"{API}{path}", headers=su, params={"skip": 1, "limit": 1})
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]) == 1
    assert r.json()["count"] == total
