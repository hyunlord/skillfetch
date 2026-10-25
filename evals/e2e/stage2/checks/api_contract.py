#!/usr/bin/env python3
"""Frozen contract script for s2-api. Run inside the session worktree:
  BOOKMARKS_DB=<tmp> uv run python api_contract.py <worktree> phase1   -> JSON lines {name, pass, detail}
  BOOKMARKS_DB=<same> uv run python api_contract.py <worktree> phase2  (new process: data persisted)
The spec is the prompt: app in app/main.py `app`; SQLite at $BOOKMARKS_DB; url (http/https only), title, tags,
created_at; POST/GET list (?tag, ?limit, ?offset)/GET one/PATCH/DELETE; duplicate url blocked; 201/204/404/409/422."""
import json
import sys
import traceback

sys.path.insert(0, sys.argv[1])
PHASE = sys.argv[2]
results = []


def items(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for k in ("items", "results", "data", "bookmarks"):
            if isinstance(body.get(k), list):
                return body[k]
    return None


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc}"[:300]
    results.append({"name": name, "pass": bool(ok), "detail": str(detail)[:300]})


try:
    from fastapi.testclient import TestClient

    from app.main import app
    c = TestClient(app, raise_server_exceptions=False)
    c.__enter__()  # run startup / lifespan handlers, as a real server would (fix 2026-10-23, see VALIDATION.md)
except Exception:  # noqa: BLE001
    print(json.dumps({"name": "import app.main:app", "pass": False, "detail": traceback.format_exc()[-300:]}))
    sys.exit(0)

if PHASE == "phase2":
    def persisted():
        r = c.get("/bookmarks")
        got = items(r.json())
        return r.status_code == 200 and got is not None and len(got) == 2, f"{r.status_code} {r.text[:150]}"
    check("data persists across processes (2 bookmarks after phase 1)", persisted)
else:
    ids = {}

    def create(key, payload):
        def run():
            r = c.post("/bookmarks", json=payload)
            b = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code == 201 and isinstance(b, dict) and "id" in b:
                ids[key] = b["id"]
            need = {"id", "url", "title", "tags", "created_at"}
            return r.status_code == 201 and isinstance(b, dict) and need <= set(b), f"{r.status_code} {str(b)[:150]}"
        return run

    def status(method, path, expect, payload=None):
        def run():
            p = path.format(**ids) if ids else path
            r = c.request(method, p, json=payload) if payload is not None else c.request(method, p)
            return r.status_code == expect, f"{r.status_code} {r.text[:150]}"
        return run

    def listing(params, n, titles=None):
        def run():
            r = c.get("/bookmarks", params=params)
            got = items(r.json())
            ok = r.status_code == 200 and got is not None and len(got) == n
            if ok and titles is not None:
                ok = sorted(x.get("title") for x in got) == sorted(titles)
            return ok, f"{r.status_code} n={None if got is None else len(got)} {r.text[:120]}"
        return run

    def field(path, key, value):
        def run():
            r = c.get(path.format(**ids))
            return r.status_code == 200 and r.json().get(key) == value, f"{r.status_code} {r.text[:150]}"
        return run

    def patch(path, payload, key, value, also=None):
        def run():
            r = c.patch(path.format(**ids), json=payload)
            b = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and b.get(key) == value
            for k, v in (also or {}).items():
                ok = ok and b.get(k) == v
            return ok, f"{r.status_code} {r.text[:150]}"
        return run

    check("POST valid bookmark -> 201 with id,url,title,tags,created_at", create("a", {"url": "https://example.com/a", "title": "A", "tags": ["x", "y"]}))
    check("POST second (http) -> 201", create("b", {"url": "http://example.org/b", "title": "B", "tags": ["y"]}))
    check("POST without tags -> 201", create("c", {"url": "https://example.net/c", "title": "C"}))
    check("POST without tags stores tags []", field("/bookmarks/{c}", "tags", []))
    check("POST duplicate url -> 409", status("POST", "/bookmarks", 409, {"url": "https://example.com/a", "title": "dup"}))
    check("POST ftp url -> 422", status("POST", "/bookmarks", 422, {"url": "ftp://example.com/f", "title": "F"}))
    check("POST non-url -> 422", status("POST", "/bookmarks", 422, {"url": "not a url", "title": "N"}))
    check("POST missing title -> 422", status("POST", "/bookmarks", 422, {"url": "https://example.com/t"}))
    check("POST missing url -> 422", status("POST", "/bookmarks", 422, {"title": "no url"}))
    check("GET list -> 3", listing({}, 3, ["A", "B", "C"]))
    check("GET ?tag=y -> A,B", listing({"tag": "y"}, 2, ["A", "B"]))
    check("GET ?tag=zzz -> 0", listing({"tag": "zzz"}, 0))
    check("GET ?limit=1 -> 1", listing({"limit": 1}, 1))
    check("GET ?limit=2&offset=2 -> 1", listing({"limit": 2, "offset": 2}, 1))
    check("GET one -> 200 title A", field("/bookmarks/{a}", "title", "A"))
    check("GET missing -> 404", status("GET", "/bookmarks/999999", 404))
    check("PATCH title -> 200, url and tags kept", patch("/bookmarks/{a}", {"title": "A2"}, "title", "A2", {"url": "https://example.com/a", "tags": ["x", "y"]}))
    check("PATCH tags -> 200", patch("/bookmarks/{a}", {"tags": ["z"]}, "tags", ["z"]))
    check("GET ?tag=x after retag -> 0", listing({"tag": "x"}, 0))
    check("GET ?tag=z after retag -> A2", listing({"tag": "z"}, 1, ["A2"]))
    check("PATCH ftp url -> 422", status("PATCH", "/bookmarks/{a}", 422, {"url": "ftp://example.com/x"}))
    check("PATCH url to another's url -> 409", status("PATCH", "/bookmarks/{b}", 409, {"url": "https://example.net/c"}))
    check("PATCH missing -> 404", status("PATCH", "/bookmarks/999999", 404, {"title": "x"}))
    check("DELETE -> 204", status("DELETE", "/bookmarks/{c}", 204))
    check("GET deleted -> 404", status("GET", "/bookmarks/{c}", 404))
    check("DELETE again -> 404", status("DELETE", "/bookmarks/{c}", 404))

for r in results:
    print(json.dumps(r))
