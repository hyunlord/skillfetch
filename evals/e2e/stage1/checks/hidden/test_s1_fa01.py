"""s1-fa-01: order_by / order on GET /items/ (normal user, items "b", "a", "c" created in that order)."""
import pytest
from fastapi.testclient import TestClient

from tests.hidden_s1.s1util import API, new_item, new_user


@pytest.fixture(scope="module")
def owner(client: TestClient) -> dict:
    u = new_user(client)
    for t in ("b", "a", "c"):
        new_item(client, u["headers"], title=t)
    return u


def _get(client, owner, params):
    return client.get(f"{API}/items/", headers=owner["headers"], params=params)


def _titles(r):
    assert r.status_code == 200, r.text
    return [i["title"] for i in r.json()["data"]]


def test_1_default_newest_first(client, owner):
    assert _titles(_get(client, owner, {})) == ["c", "a", "b"]


def test_2_title_asc(client, owner):
    assert _titles(_get(client, owner, {"order_by": "title", "order": "asc"})) == ["a", "b", "c"]


def test_3_title_desc(client, owner):
    assert _titles(_get(client, owner, {"order_by": "title", "order": "desc"})) == ["c", "b", "a"]


def test_4_created_at_asc(client, owner):
    assert _titles(_get(client, owner, {"order_by": "created_at", "order": "asc"})) == ["b", "a", "c"]


def test_5_bad_order_by_422(client, owner):
    assert _get(client, owner, {"order_by": "owner_id"}).status_code == 422


def test_6_bad_order_422(client, owner):
    assert _get(client, owner, {"order": "up"}).status_code == 422


def test_7_count_is_3(client, owner):
    for params in ({}, {"order_by": "title", "order": "asc"}, {"order_by": "title", "order": "desc"},
                   {"order_by": "created_at", "order": "asc"}):
        r = _get(client, owner, params)
        if r.status_code == 200:
            assert r.json()["count"] == 3, params
