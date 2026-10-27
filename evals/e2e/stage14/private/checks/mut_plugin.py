"""pytest plugin for Stage 14 task 3 (API tests): wraps the session's own `app.main.app` in an ASGI middleware that changes
one behaviour of the bookmarks contract, chosen by $S14_MUT. Loaded with `-p mut_plugin` (PYTHONPATH = this folder).
Mutants (fixed before the run, DESIGN §9):
  not_found_200   any 404 response becomes 200
  dup_allowed     any 409 response becomes 201
  validation_off  any 422 response becomes 201 (POST) or 200 (other methods)
  create_200      POST 201 becomes 200
  delete_200      DELETE 204 becomes 200
  limit_ignored   GET /bookmarks: the `limit` query parameter is dropped
  tag_ignored     GET /bookmarks: the `tag` query parameter is dropped
  offset_ignored  GET /bookmarks: the `offset` query parameter is dropped
Applied to every Starlette/FastAPI app the tests call (their __call__ is wrapped), so the tests' own\napp construction does not matter. Tests that call a live server in another process are not affected (not killed)."""
import os
from urllib.parse import parse_qsl, urlencode

KIND = os.environ.get("S14_MUT", "")
DROP = {"limit_ignored": "limit", "tag_ignored": "tag", "offset_ignored": "offset"}


class Mut:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        method, path = scope.get("method", ""), scope.get("path", "").rstrip("/")
        if KIND in DROP and method == "GET" and path == "/bookmarks":
            q = [(k, v) for k, v in parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True) if k != DROP[KIND]]
            scope = dict(scope, query_string=urlencode(q).encode())

        async def send2(msg):
            if msg.get("type") == "http.response.start":
                s = msg.get("status")
                new = s
                if KIND == "not_found_200" and s == 404:
                    new = 200
                elif KIND == "dup_allowed" and s == 409:
                    new = 201
                elif KIND == "validation_off" and s == 422:
                    new = 201 if method == "POST" else 200
                elif KIND == "create_200" and method == "POST" and s == 201:
                    new = 200
                elif KIND == "delete_200" and method == "DELETE" and s == 204:
                    new = 200
                if new != s:
                    msg = dict(msg, status=new)
            await send(msg)
        return await self.app(scope, receive, send2)


def pytest_configure(config):
    """Every Starlette/FastAPI app called during the run goes through the mutant first (also apps made by a factory or
    after a module reload): __call__ of Starlette and of FastAPI (which has its own) is wrapped; a scope flag keeps the
    mutant from applying twice when FastAPI.__call__ calls Starlette.__call__."""
    if not KIND:
        return
    classes = []
    try:
        from starlette.applications import Starlette
        classes.append(Starlette)
    except Exception:  # noqa: BLE001
        return
    try:
        from fastapi import FastAPI
        classes.append(FastAPI)
    except Exception:  # noqa: BLE001
        pass
    for cls in classes:
        if "__call__" not in cls.__dict__:
            continue
        orig = cls.__dict__["__call__"]

        def make(orig):
            async def call(self, scope, receive, send):
                if scope.get("type") != "http" or scope.get("s14_mut"):
                    return await orig(self, scope, receive, send)
                scope = dict(scope, s14_mut=True)
                return await Mut(lambda s, r, se: orig(self, s, r, se))(scope, receive, send)
            return call
        cls.__call__ = make(orig)
