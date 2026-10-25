from fastapi.testclient import TestClient


def test_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("BOOKMARKS_DB", str(tmp_path / "t.db"))
    from app.main import app
    c = TestClient(app)
    r = c.post("/bookmarks", json={"url": "https://a.example", "title": "A"})
    assert r.status_code == 201
    assert c.get(f"/bookmarks/{r.json()['id']}").status_code == 200
