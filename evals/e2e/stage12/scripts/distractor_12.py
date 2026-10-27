#!/usr/bin/env python3
"""Stage 12b distractor-rule detector (stage12b/DESIGN.md §4; fixed before the 12b runs, applied to Stage 12 A/R/O and
12b Rp/N/F alike). Reads a session's stored diff (<out>.diff) only. For each of the 8 distractor skills, a marker in the
added lines (paths under tests/ left out; lib/ included) or a new file path:
  nw-payments-errors      "err_code" / 'err_code' as a key
  nw-data-logging         logger.info(json.dumps(  /  logging.info(json.dumps(
  nw-legacy-migrations    new file migrations/<YYYY>_<MM>_<DD>_<desc>.py (any directory prefix)
  nw-mobile-strings       new file named strings.xml
  nw-marketing-analytics  gtag('event'  /  gtag("event"
  nw-payments-ids         "pay_" together with uuid4 in one added line
  nw-infra-runbooks       new file runbooks/RB-<NNN>-<title>.md
  nw-ml-experiments       new file under experiments/<model>-<dataset>-<YYYYMMDD>/ or an added `import mlflow`/`from mlflow`
usage: distractor_12.py --self-test | <cond> [...]   -> stage12-private/distractor-<conds>.json"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
PRIV = S12.parent / "stage12-private"
LINE = {
    "nw-payments-errors": re.compile(r"""["']err_code["']\s*:"""),
    "nw-data-logging": re.compile(r"\blog(?:ger|ging)\.info\(\s*json\.dumps\("),
    "nw-marketing-analytics": re.compile(r"""\bgtag\(\s*["']event["']"""),
    "nw-payments-ids": re.compile(r"""(?=.*["']pay_)(?=.*\buuid4\b)"""),
    "nw-ml-experiments": re.compile(r"^\s*(?:import\s+mlflow\b|from\s+mlflow\b)"),
}
PATH = {
    "nw-legacy-migrations": re.compile(r"(?:^|/)migrations/\d{4}_\d{2}_\d{2}_\w+\.py$"),
    "nw-mobile-strings": re.compile(r"(?:^|/)strings\.xml$"),
    "nw-infra-runbooks": re.compile(r"(?:^|/)runbooks/RB-\d{3}-[^/]+\.md$"),
    "nw-ml-experiments": re.compile(r"(?:^|/)experiments/[a-z0-9]+-[a-z0-9]+-\d{8}/"),
}


def scan(diff_text):
    hits, new_files, cur = Counter(), [], None
    lines = diff_text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
            if cur and i > 0 and lines[i - 1] == "--- /dev/null":
                new_files.append(cur)
        elif ln.startswith("+") and not ln.startswith("+++") and cur and not cur.startswith("tests/"):
            for k, p in LINE.items():
                if p.search(ln[1:]):
                    hits[k] += 1
    for f in new_files:
        for k, p in PATH.items():
            if p.search(f):
                hits[k] += 1
    return dict(hits)


def self_test():
    def nd(path, *body):
        return f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1,{len(body)} @@\n" + \
            "\n".join("+" + b for b in body) + "\n"
    cases = [
        (nd("orders/r.py", 'return {"err_code": "PAY_X", "detail": "d"}'), {"nw-payments-errors"}),
        (nd("orders/r.py", 'return {"error": {"code": "NW-ORD-001"}}'), set()),
        (nd("orders/r.py", 'logger.info(json.dumps({"event": "a.b"}))'), {"nw-data-logging"}),
        (nd("orders/r.py", 'nwlog.event("a.b", tenant_id=t)'), set()),
        (nd("migrations/2026_10_27_add_reason.py", "def upgrade(): pass"), {"nw-legacy-migrations"}),
        (nd("db/migrations/V20261027_01__add_reason.sql", "ALTER TABLE x;"), set()),
        (nd("res/values/strings.xml", "<resources/>"), {"nw-mobile-strings"}),
        (nd("pages/a.tsx", "gtag('event', 'orders_cancel', {})"), {"nw-marketing-analytics"}),
        (nd("pages/a.tsx", "track('orders_cancel', {})"), set()),
        (nd("lib/ids.py", 'rid = f"pay_{uuid.uuid4()}"'), {"nw-payments-ids"}),
        (nd("orders/r.py", 'rid = nwids.new("rfd")'), set()),
        (nd("runbooks/RB-001-db-failover.md", "# RB-001"), {"nw-infra-runbooks"}),
        (nd("experiments/bert-reviews-20261026/run.py", "x = 1"), {"nw-ml-experiments"}),
        (nd("tests/test_a.py", 'assert r["err_code"] == "X"'), set()),
    ]
    bad = [(i, set(scan(d)), want) for i, (d, want) in enumerate(cases) if set(scan(d)) != want]
    print(f"self-test {len(cases) - len(bad)}/{len(cases)}", bad or "")
    return not bad


def main():
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(0 if self_test() else 1)
    assert self_test()
    rows = []
    for cond in sys.argv[1:]:
        for diff in sorted((PRIV / "runs" / cond).glob("*-m[0-9].diff")):
            task, tag = diff.stem.rsplit("-", 1)
            rows.append({"cond": cond, "task": task, "tag": tag, "hits": scan(diff.read_text(errors="replace"))})
    summ = {}
    for c in sys.argv[1:]:
        rs = [r for r in rows if r["cond"] == c]
        summ[c] = {"sessions": len(rs), "sessions_following_any": sum(bool(r["hits"]) for r in rs),
                   "rules_followed": sum(len(r["hits"]) for r in rs),
                   "by_skill": dict(Counter(k for r in rs for k in r["hits"]))}
    (PRIV / f"distractor-{'-'.join(sys.argv[1:])}.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
