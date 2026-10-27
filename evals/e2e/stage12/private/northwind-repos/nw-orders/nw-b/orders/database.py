"""Database connection and initialization."""
import os
import sqlite3


def get_db() -> sqlite3.Connection:
    path = os.environ.get("DATABASE_URL", "orders.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price_minor INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        from datetime import datetime, timezone

        from lib.nwids import new as nwids_new

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for name, price, desc in [
            ("Widget", 999, "Standard widget"),
            ("Gadget", 2499, "Premium gadget"),
            ("Doohickey", 499, "Basic doohickey"),
        ]:
            conn.execute(
                "INSERT INTO products (public_id, name, description, price_minor, currency, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nwids_new("prod"), name, desc, price, "USD", now, now),
            )
        conn.commit()
    conn.close()
