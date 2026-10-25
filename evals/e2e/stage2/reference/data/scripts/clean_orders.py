"""Reference cleaner (validation only)."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "orders.csv", dtype=str).drop_duplicates()
df["unit_price"] = pd.to_numeric(df["unit_price"].str.replace(r"[^0-9.]", "", regex=True), errors="coerce")
df["quantity"] = pd.to_numeric(df["quantity"].str.extract(r"(-?\d+)")[0], errors="coerce")
out = ROOT / "out"
out.mkdir(exist_ok=True)
df.to_csv(out / "orders_clean.csv", index=False)
(out / "report.md").write_text(f"# Orders\n\nrows: {len(df)}\n")
