#!/usr/bin/env python3
"""Seeded generator for repos/s2-data/data/orders.csv and the list of planted problems (orders-truth.json).
Not given to sessions."""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

rng = random.Random(20261023)
OUT = Path(__file__).resolve().parents[2] / "repos" / "s2-data" / "data" / "orders.csv"
TRUTH = Path(__file__).resolve().parent / "orders-truth.json"

PRODUCTS = [("Wireless Mouse", "Electronics", 24.99), ("USB-C Hub, 7-in-1", "Electronics", 49.0),
            ("Standing Desk", "Furniture", 389.0), ("Desk Lamp", "Furniture", 32.5), ("Notebook A5", "Stationery", 4.2),
            ("Gel Pens (12)", "Stationery", 9.99), ("Monitor 27\"", "Electronics", 1249.0), ("Office Chair", "Furniture", 214.0),
            ("Coffee Beans 1kg", "Grocery", 18.75), ("Green Tea (50 bags)", "Grocery", 6.4)]
CAT_VARIANTS = {"Electronics": ["Electronics", " electronics", "ELECTRONICS", "Elec."],
                "Furniture": ["Furniture", "furniture ", "FURNITURE"], "Stationery": ["Stationery", "stationary", "STATIONERY"],
                "Grocery": ["Grocery", "groceries", " Grocery"]}
COUNTRIES = {"US": ["US", "USA", "United States", "u.s."], "DE": ["DE", "Germany", "germany"], "KR": ["KR", "South Korea", "Korea, Republic of"],
             "GB": ["GB", "UK", "United Kingdom"]}
STATUS = {"shipped": ["shipped", "Shipped ", "SHIPPED"], "cancelled": ["cancelled", "canceled", "Cancelled"],
          "pending": ["pending", "Pending", " pending"], "returned": ["returned", "RETURNED"]}


def fmt_date(d, kind):
    return {"iso": d.isoformat(), "dmy": d.strftime("%d/%m/%Y"), "long": d.strftime("%B %-d %Y"),
            "slash": d.strftime("%Y/%m/%d"), "blank": ""}[kind]


def fmt_price(p, kind):
    return {"plain": f"{p:.2f}", "dollar": f"${p:,.2f}", "usd": f"USD {p:.2f}", "comma": f"{p:,.2f}", "blank": ""}[kind]


def main():
    truth = {"rows_written": 0, "exact_duplicate_rows": 0, "conflicting_duplicate_ids": [], "date_formats": {},
             "price_formats": {}, "blank_dates": 0, "blank_prices": 0, "blank_quantity": 0, "quantity_with_units": 0,
             "negative_quantity": 0, "zero_quantity": 0, "invalid_emails": 0, "blank_emails": 0, "uppercase_emails": 0,
             "discount_formats": {}, "category_variants": CAT_VARIANTS, "country_variants": COUNTRIES, "status_variants": STATUS,
             "future_dates": 0, "outlier_prices": 0}
    rows = []
    start = date(2025, 1, 1)
    for i in range(1, 361):
        name, cat, price = rng.choice(PRODUCTS)
        d = start + timedelta(days=rng.randrange(0, 300))
        dk = rng.choices(["iso", "dmy", "long", "slash", "blank"], [60, 15, 8, 12, 5])[0]
        pk = rng.choices(["plain", "dollar", "usd", "comma", "blank"], [55, 20, 8, 12, 5])[0]
        q = rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 10])
        qs = str(q)
        roll = rng.random()
        if roll < 0.04:
            qs = ""
            truth["blank_quantity"] += 1
        elif roll < 0.08:
            qs = f"{q} pcs"
            truth["quantity_with_units"] += 1
        elif roll < 0.11:
            qs = str(-q)
            truth["negative_quantity"] += 1
        elif roll < 0.13:
            qs = "0"
            truth["zero_quantity"] += 1
        p = price
        if rng.random() < 0.015:
            p = price * 100
            truth["outlier_prices"] += 1
        user = rng.choice(["ana", "ben", "chloe", "dmitri", "eun-ji", "farah", "gus", "hana", "ivan", "jun"])
        email = f"{user}{rng.randrange(1, 60)}@example.com"
        er = rng.random()
        if er < 0.05:
            email = ""
            truth["blank_emails"] += 1
        elif er < 0.09:
            email = rng.choice([email.replace("@", ""), email.replace(".com", ""), email + " ", "n/a"])
            truth["invalid_emails"] += 1 if email.strip() not in ("",) and "@" not in email or email.endswith("@example") or email == "n/a" else 0
        elif er < 0.13:
            email = email.upper()
            truth["uppercase_emails"] += 1
        disc_k = rng.choices(["blank", "pct", "frac", "zero"], [50, 20, 20, 10])[0]
        dv = rng.choice([5, 10, 15, 20])
        disc = {"blank": "", "pct": f"{dv}%", "frac": f"{dv / 100:.2f}", "zero": "0"}[disc_k]
        if rng.random() < 0.02:
            d = date(2027, rng.randrange(1, 13), rng.randrange(1, 28))
            dk = "iso"
            truth["future_dates"] += 1
        country = rng.choice(list(COUNTRIES))
        status = rng.choices(list(STATUS), [70, 10, 15, 5])[0]
        rows.append({"order_id": f"ORD-{i:05d}", "order_date": fmt_date(d, dk), "customer_email": email,
                     "country": rng.choice(COUNTRIES[country]), "product": name, "category": rng.choice(CAT_VARIANTS[cat]),
                     "quantity": qs, "unit_price": fmt_price(p, pk), "discount": disc, "status": rng.choice(STATUS[status])})
        truth["date_formats"][dk] = truth["date_formats"].get(dk, 0) + 1
        truth["price_formats"][pk] = truth["price_formats"].get(pk, 0) + 1
        truth["discount_formats"][disc_k] = truth["discount_formats"].get(disc_k, 0) + 1
    truth["blank_dates"] = truth["date_formats"].get("blank", 0)
    truth["blank_prices"] = truth["price_formats"].get("blank", 0)
    for r in rng.sample(rows, 12):  # exact duplicates
        rows.insert(rng.randrange(len(rows)), dict(r))
        truth["exact_duplicate_rows"] += 1
    for r in rng.sample(rows[:300], 3):  # same order_id, different content
        c = dict(r, quantity="7", status="pending")
        rows.insert(rng.randrange(len(rows)), c)
        truth["conflicting_duplicate_ids"].append(r["order_id"])
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    truth["rows_written"] = len(rows)
    TRUTH.write_text(json.dumps(truth, indent=1))
    print(len(rows), json.dumps({k: v for k, v in truth.items() if not k.endswith("variants")}))


if __name__ == "__main__":
    main()
