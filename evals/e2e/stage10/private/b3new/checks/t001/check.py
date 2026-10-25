#!/usr/bin/env python3
"""Hidden objective check for t001:
"add --dry-run to scripts/reconcile_payouts.py, print the diff instead of writing rows"

Usage: python3 check.py <worktree> <outdir> [--reply <file>]   (--reply is ignored)

All fixture files live in a temp dir outside the worktree; nothing is copied into
the worktree. Commands run inside the worktree via `uv run` (worktree already synced).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = "t001"
TIMEOUT = 600
SCRIPT = "scripts/reconcile_payouts.py"

# --- fixture (distinct from the repo's sample data) -------------------------
LEDGER = [  # payout_id, merchant_id, amount_cents, status
    ("po_7f3a01", "m_101", 128450, "paid"),
    ("po_7f3a02", "m_102", 48250, "paid"),
    ("po_7f3a03", "m_103", 9999, "paid"),
    ("po_7f3a04", "m_104", 315075, "paid"),
    ("po_7f3a05", "m_105", 22010, "paid"),
    ("po_7f3a06", "m_106", 70300, "paid"),
    ("po_7f3a07", "m_107", 5525, "paid"),
    ("po_7f3a08", "m_108", 41870, "paid"),
    ("po_7f3a09", "m_109", 16640, "paid"),
    ("po_7f3a10", "m_110", 83300, "pending"),
    ("po_7f3a11", "m_111", 60125, "paid"),
]
SETTLEMENTS = [  # payout_id, amount (decimal currency)
    ("po_7f3a01", "1284.50"),
    ("po_7f3a02", "470.00"),
    ("po_7f3a03", "99.99"),
    ("po_7f3a04", "3158.15"),
    ("po_7f3a06", "703.00"),
    ("po_7f3a07", "52.36"),
    ("po_7f3a11", "601.25"),
    ("po_7f3a90", "211.40"),
    ("po_7f3a91", "18.07"),
]
# (payout_id, expected_cents, settled_cents, delta_cents, reason)
EXPECTED = [
    ("po_7f3a02", 48250, 47000, -1250, "amount_mismatch"),
    ("po_7f3a04", 315075, 315815, 740, "amount_mismatch"),
    ("po_7f3a07", 5525, 5236, -289, "amount_mismatch"),
    ("po_7f3a05", 22010, 0, -22010, "missing_from_settlement"),
    ("po_7f3a08", 41870, 0, -41870, "missing_from_settlement"),
    ("po_7f3a09", 16640, 0, -16640, "missing_from_settlement"),
    ("po_7f3a90", 0, 21140, 21140, "unknown_payout"),
    ("po_7f3a91", 0, 1807, 1807, "unknown_payout"),
]

PAYOUTS_DDL = """CREATE TABLE payouts (
    payout_id TEXT PRIMARY KEY, merchant_id TEXT NOT NULL, amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD', status TEXT NOT NULL, created_at TEXT NOT NULL)"""
ADJ_DDL = """CREATE TABLE payout_adjustments (
    id INTEGER PRIMARY KEY, payout_id TEXT, expected_cents INTEGER, settled_cents INTEGER,
    delta_cents INTEGER, reason TEXT, created_at TEXT)"""

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def make_fixture(tmp: Path) -> tuple[Path, Path]:
    db = tmp / "fixture_ledger.db"
    conn = sqlite3.connect(db)
    conn.execute(PAYOUTS_DDL)
    conn.execute(ADJ_DDL)
    conn.executemany(
        "INSERT INTO payouts VALUES (?, ?, ?, 'USD', ?, '2024-09-14T08:00:00Z')", LEDGER
    )
    conn.commit()
    conn.close()
    csv_path = tmp / "fixture_settlements.csv"
    lines = ["payout_id,amount,currency,settled_at"]
    lines += [f"{pid},{amt},USD,2024-09-16T02:00:00Z" for pid, amt in SETTLEMENTS]
    csv_path.write_text("\n".join(lines) + "\n")
    return db, csv_path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tail(text: str, n: int = 600) -> str:
    text = text.strip()
    return text if len(text) <= n else "..." + text[-n:]


def run(cmd: list[str], cwd: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "LEDGER_DB")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["NO_COLOR"] = "1"
    if env_extra:
        env.update(env_extra)
    try:
        return subprocess.run(
            cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return subprocess.CompletedProcess(cmd, 124, out, err + f"\n[timeout after {TIMEOUT}s]")


def run_script(worktree: Path, db: Path, csv_path: Path, extra: list[str]) -> subprocess.CompletedProcess:
    return run(
        ["uv", "run", "python", SCRIPT, "--settlements", str(csv_path), "--db", str(db), *extra],
        worktree,
        {"LEDGER_DB": str(db)},
    )


def amount_forms(cents: int) -> list[str]:
    v = abs(cents)
    forms = {str(v), f"{v:,}", f"{v / 100:.2f}", f"{v / 100:,.2f}", repr(v / 100)}
    if v % 100 == 0:
        forms.add(str(v // 100))
        forms.add(f"{v // 100:,}")
    return sorted(forms, key=len, reverse=True)


def has_amount(text: str, cents: int) -> bool:
    for form in amount_forms(cents):
        if re.search(r"(?<![\d.,])" + re.escape(form) + r"(?!\d)", text):
            return True
    return False


def window_for(lines: list[str], payout_id: str) -> str | None:
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(payout_id) + r"(?![A-Za-z0-9_])")
    hits = [i for i, line in enumerate(lines) if pat.search(line)]
    if not hits:
        return None
    chunks = []
    for i in hits:
        chunks.extend(lines[max(0, i - 1): i + 6])
    return "\n".join(chunks)


def adjustment_rows(db: Path) -> list[tuple]:
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return conn.execute(
            "SELECT payout_id, expected_cents, settled_cents, delta_cents, reason "
            "FROM payout_adjustments"
        ).fetchall()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree")
    ap.add_argument("outdir")
    ap.add_argument("--reply", default=None)
    ap.add_argument("--base", default="s10-a")  # passed by run_s10.py; not needed for t001
    args = ap.parse_args()
    worktree = Path(args.worktree).resolve()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    items: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        items.append({"name": name, "pass": bool(ok), "detail": detail})

    tmp = Path(tempfile.mkdtemp(prefix="t001-check-"))
    try:
        fixture_db, csv_path = make_fixture(tmp)

        # a. tests pass
        r = run(["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "tests/"], worktree)
        out = r.stdout + r.stderr
        last = out.strip().splitlines()[-1] if out.strip() else ""
        add("a_tests_pass", r.returncode == 0,
            f"rc=0: {last}" if r.returncode == 0 else f"rc={r.returncode}: {tail(out)}")

        # b + c. dry-run writes nothing and prints the diff
        dry_dir = tmp / "dry"
        dry_dir.mkdir()
        dry_db = dry_dir / "ledger.db"
        shutil.copy2(fixture_db, dry_db)
        before = sha256(dry_db)
        r = run_script(worktree, dry_db, csv_path, ["--dry-run"])
        after = sha256(dry_db)
        sidecars = [p.name for p in dry_dir.iterdir() if p.name != "ledger.db" and p.stat().st_size > 0]
        b_ok = r.returncode == 0 and before == after and not sidecars
        if b_ok:
            b_detail = "rc=0, db sha256 unchanged"
        else:
            b_detail = (f"rc={r.returncode}, db_unchanged={before == after}, sidecars={sidecars}: "
                        + tail(r.stdout + r.stderr, 500))
        add("b_dry_run_writes_nothing", b_ok, b_detail)

        stdout = ANSI.sub("", r.stdout)
        lines = stdout.splitlines()
        problems = []
        for pid, exp, settled, delta, reason in EXPECTED:
            win = window_for(lines, pid)
            if win is None:
                problems.append(f"{pid}: not mentioned")
                continue
            if reason == "amount_mismatch":
                if not (has_amount(win, delta) or (has_amount(win, exp) and has_amount(win, settled))):
                    problems.append(f"{pid}: no delta ({delta}) or both amounts ({exp}/{settled})")
        c_ok = r.returncode == 0 and not problems
        if c_ok:
            c_detail = f"all {len(EXPECTED)} payout_ids mentioned; mismatch amounts shown"
        else:
            c_detail = f"rc={r.returncode}; " + "; ".join(problems) + " | stdout: " + tail(stdout, 400)
        add("c_dry_run_prints_diff", c_ok, tail(c_detail))

        # d. normal run unchanged
        real_dir = tmp / "real"
        real_dir.mkdir()
        real_db = real_dir / "ledger.db"
        shutil.copy2(fixture_db, real_db)
        pre_rows = collections.Counter(adjustment_rows(real_db))
        r = run_script(worktree, real_db, csv_path, [])
        try:
            post_rows = collections.Counter(adjustment_rows(real_db))
            new_rows = post_rows - pre_rows
            err = ""
        except sqlite3.Error as exc:
            new_rows, err = collections.Counter(), f"sqlite error: {exc}"
        expected = collections.Counter(EXPECTED)
        d_ok = r.returncode == 0 and new_rows == expected and not err
        if d_ok:
            d_detail = f"rc=0, {sum(new_rows.values())} expected rows written"
        else:
            missing = sorted((expected - new_rows).elements())
            extra = sorted((new_rows - expected).elements())
            d_detail = (f"rc={r.returncode} {err} missing={missing} extra={extra} | "
                        + tail(r.stdout + r.stderr, 300))
        add("d_normal_run_unchanged", d_ok, tail(d_detail))

        # e. --help mentions --dry-run
        r = run(["uv", "run", "python", SCRIPT, "--help"], worktree)
        e_ok = r.returncode == 0 and "--dry-run" in r.stdout
        add("e_help_lists_dry_run", e_ok,
            "--dry-run in --help" if e_ok else f"rc={r.returncode}: {tail(r.stdout + r.stderr)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    result = {"task": TASK, "pass": all(i["pass"] for i in items), "items": items}
    (outdir / "check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"task": TASK, "pass": result["pass"],
                      "items": {i["name"]: i["pass"] for i in items}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
