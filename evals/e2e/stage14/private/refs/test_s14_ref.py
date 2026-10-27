"""Stage 14 task 3 reference tests (validation only): one test per contract behaviour the mutants change."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def c(monkeypatch):
    d = tempfile.mkdtemp()
    monkeypatch.setenv("BOOKMARKS_DB", os.path.join(d, "ref.db"))
    import importlib
    import app.main as m
    m = importlib.reload(m)
    with TestClient(m.app) as client:
        yield client


def mk(c, n, tags=()):
    return c.post("/bookmarks", json={"url": f"https://e{n}.example.com", "title": f"t{n}", "tags": list(tags)})


def items(r):
    b = r.json()
    return b if isinstance(b, list) else next(v for k, v in b.items() if isinstance(v, list))


def test_create_201(c):
    assert mk(c, 1).status_code == 201


def test_missing_404(c):
    assert c.get("/bookmarks/999999").status_code == 404


def test_duplicate_409(c):
    mk(c, 1)
    assert mk(c, 1).status_code == 409


def test_bad_url_422(c):
    assert c.post("/bookmarks", json={"url": "ftp://x", "title": "t"}).status_code == 422


def test_delete_204(c):
    i = mk(c, 1).json()["id"]
    assert c.delete(f"/bookmarks/{i}").status_code == 204


def test_limit(c):
    for n in range(3):
        mk(c, n)
    assert len(items(c.get("/bookmarks?limit=2"))) == 2


def test_offset(c):
    for n in range(3):
        mk(c, n)
    assert len(items(c.get("/bookmarks?offset=2"))) == 1


def test_tag(c):
    mk(c, 1, ["a"])
    mk(c, 2, ["b"])
    assert len(items(c.get("/bookmarks?tag=a"))) == 1
