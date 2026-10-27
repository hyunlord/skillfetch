def test_create_order(client):
    resp = client.post(
        "/orders",
        json={"customer_id": 1, "product": "Widget", "quantity": 2, "unit_price": 5.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["product"] == "Widget"
    assert data["total"] == 10.0


def test_get_order(client):
    create = client.post(
        "/orders",
        json={"customer_id": 1, "product": "Gadget", "quantity": 1, "unit_price": 25.0},
    )
    order_id = create.json()["id"]
    resp = client.get(f"/orders/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["product"] == "Gadget"


def test_get_order_not_found(client):
    resp = client.get("/orders/9999")
    assert resp.status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
