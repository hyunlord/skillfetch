import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    os.environ["DATABASE_URL"] = db_path
    from orders.database import init_db

    init_db()
    yield db_path


@pytest.fixture
def client():
    from orders.app import app

    return TestClient(app)


class _NWFactory:
    """Factory for creating test entities."""

    def __init__(self, c):
        self._client = c

    def order(self, **overrides):
        defaults = {
            "customer_id": 1,
            "product": "Widget",
            "quantity": 1,
            "unit_price": 9.99,
        }
        defaults.update(overrides)
        return defaults


@pytest.fixture
def nw_factory(client):
    return _NWFactory(client)
