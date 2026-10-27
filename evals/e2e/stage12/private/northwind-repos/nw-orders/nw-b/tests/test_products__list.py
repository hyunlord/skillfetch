import pytest


@pytest.mark.contract
def test_list_products_returns_paginated(client, nw_factory):
    resp = client.get("/products?limit=10")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "next_cursor" in body
    assert isinstance(body["data"], list)


@pytest.mark.contract
def test_get_product_not_found(client):
    resp = client.get("/products/prod_nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "NW-PROD-001"


@pytest.mark.contract
def test_get_product_success(client):
    list_resp = client.get("/products?limit=1")
    items = list_resp.json()["data"]
    assert len(items) > 0
    pid = items[0]["id"]
    resp = client.get(f"/products/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == pid
    assert "created_at" in data
    assert data["created_at"].endswith("Z")
