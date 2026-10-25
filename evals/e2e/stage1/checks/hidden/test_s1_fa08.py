"""s1-fa-08: PUT /items/{id} with title null is a validation error; description stays clearable."""
from fastapi.testclient import TestClient

from tests.hidden_s1.s1util import API, new_item, new_user


def test_title_null_422_and_unchanged(client: TestClient):
    u = new_user(client)
    item = new_item(client, u["headers"], title="orig", description="d")
    r = client.put(f"{API}/items/{item['id']}", headers=u["headers"], json={"title": None})
    assert r.status_code == 422, r.text
    r = client.get(f"{API}/items/{item['id']}", headers=u["headers"])
    assert r.status_code == 200 and r.json()["title"] == "orig"


def test_description_null_200(client: TestClient):
    u = new_user(client)
    item = new_item(client, u["headers"], title="orig", description="d")
    r = client.put(f"{API}/items/{item['id']}", headers=u["headers"], json={"description": None})
    assert r.status_code == 200, r.text
    assert r.json()["description"] is None
    r = client.get(f"{API}/items/{item['id']}", headers=u["headers"])
    assert r.json()["description"] is None


def test_title_x_200(client: TestClient):
    u = new_user(client)
    item = new_item(client, u["headers"], title="orig")
    r = client.put(f"{API}/items/{item['id']}", headers=u["headers"], json={"title": "x"})
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "x"
