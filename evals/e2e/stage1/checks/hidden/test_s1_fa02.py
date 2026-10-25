"""s1-fa-02: Item.is_done through create / update / read."""
from fastapi.testclient import TestClient

from tests.hidden_s1.s1util import API, new_item, new_user


def test_create_default_false(client: TestClient):
    u = new_user(client)
    assert new_item(client, u["headers"])["is_done"] is False


def test_update_true_and_read(client: TestClient):
    u = new_user(client)
    item = new_item(client, u["headers"])
    r = client.put(f"{API}/items/{item['id']}", headers=u["headers"], json={"is_done": True})
    assert r.status_code == 200, r.text
    assert r.json()["is_done"] is True
    r = client.get(f"{API}/items/{item['id']}", headers=u["headers"])
    assert r.status_code == 200 and r.json()["is_done"] is True
    r = client.get(f"{API}/items/", headers=u["headers"])
    assert r.status_code == 200
    assert [i["is_done"] for i in r.json()["data"] if i["id"] == item["id"]] == [True]


def test_create_true(client: TestClient):
    u = new_user(client)
    assert new_item(client, u["headers"], is_done=True)["is_done"] is True
