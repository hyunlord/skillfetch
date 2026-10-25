"""Reference implementation (validation only)."""
import json
import os
import sqlite3
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, HttpUrl

app = FastAPI(title="Bookmarks")


def db():
    con = sqlite3.connect(os.environ.get("BOOKMARKS_DB", "bookmarks.db"))
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL, tags TEXT NOT NULL, created_at TEXT NOT NULL)")
    return con


class Create(BaseModel):
    url: HttpUrl
    title: str = Field(min_length=1)
    tags: list[str] = []


class Update(BaseModel):
    url: HttpUrl | None = None
    title: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None


def out(row):
    return {"id": row["id"], "url": row["url"], "title": row["title"], "tags": json.loads(row["tags"]), "created_at": row["created_at"]}


@app.post("/bookmarks", status_code=201)
def create(b: Create):
    con = db()
    try:
        cur = con.execute("INSERT INTO bookmarks (url, title, tags, created_at) VALUES (?,?,?,?)",
                          (str(b.url), b.title, json.dumps(b.tags), datetime.now(UTC).isoformat()))
        con.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "url already saved") from None
    return out(con.execute("SELECT * FROM bookmarks WHERE id=?", (cur.lastrowid,)).fetchone())


@app.get("/bookmarks")
def list_(tag: str | None = None, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    rows = [out(r) for r in db().execute("SELECT * FROM bookmarks ORDER BY id")]
    if tag is not None:
        rows = [r for r in rows if tag in r["tags"]]
    return rows[offset: offset + limit]


def get_row(con, i):
    row = con.execute("SELECT * FROM bookmarks WHERE id=?", (i,)).fetchone()
    if row is None:
        raise HTTPException(404, "not found")
    return row


@app.get("/bookmarks/{i}")
def get(i: int):
    return out(get_row(db(), i))


@app.patch("/bookmarks/{i}")
def patch(i: int, b: Update):
    con = db()
    get_row(con, i)
    data = b.model_dump(exclude_unset=True)
    for k, v in data.items():
        v = json.dumps(v) if k == "tags" else str(v)
        try:
            con.execute(f"UPDATE bookmarks SET {k}=? WHERE id=?", (v, i))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "url already saved") from None
    con.commit()
    return out(get_row(con, i))


@app.delete("/bookmarks/{i}", status_code=204)
def delete(i: int):
    con = db()
    get_row(con, i)
    con.execute("DELETE FROM bookmarks WHERE id=?", (i,))
    con.commit()
    return Response(status_code=204)
