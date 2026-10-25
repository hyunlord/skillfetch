# Stage 2 check validation

| task | tree | check pass | items |
|---|---|---|---|
| s2-tests | base | False | src/recur unchanged: ok; session's tests run and pass: FAIL {"junit": {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "passed": 0}} |
| s2-tests | reference | True | src/recur unchanged: ok; session's tests run and pass: ok {"junit": {"tests": 30, "failures": 0, "errors": 0, "skipped": 0, "passed": 30}, "rules_line_pct": 100.0, "rules_branch_pct": 98.04} |
| s2-api | base | False | session's tests run and pass: FAIL; contract script 0/27: FAIL {"junit": {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "passed": 0}, "contract_pass": 0} |
| s2-api | reference | True | session's tests run and pass: ok; contract script 27/27: ok {"junit": {"tests": 1, "failures": 0, "errors": 0, "skipped": 0, "passed": 1}, "contract_pass": 27} |
| s2-docs | base | False | README.md at the repo root: FAIL; npm scripts named in the docs exist in package.json: ok; npm run build still passes: ok {"readme_words": 0} |
| s2-docs | reference | True | README.md at the repo root: ok; npm scripts named in the docs exist in package.json: ok; npm run build still passes: ok {"readme_words": 63} |
| s2-data | base | False | scripts/clean_orders.py exists: FAIL; uv run python scripts/clean_orders.py exits 0: FAIL; out/ has a cleaned CSV and a report: FAIL; data/orders.csv unchanged: ok {"outputs": []} |
| s2-data | reference | True | scripts/clean_orders.py exists: ok; uv run python scripts/clean_orders.py exits 0: ok; out/ has a cleaned CSV and a report: ok; data/orders.csv unchanged: ok {"outputs": ["orders_clean.csv", "report.md"]} |

## Change after the runs started (2026-10-23 ~01:00 KST)

`checks/api_contract.py` created `TestClient(app)` without entering it, so FastAPI startup/lifespan handlers never ran;
an app that creates its table in `lifespan` got 500 on every write (first seen: s2-api-B-r3, 5/27 while its own 61
tests passed). Fix: `c.__enter__()` after creating the client (as a server would run startup). Re-validated: base
fails, reference 27/27 (`validation/s2-api-*.after-fix.json`). Every s2-api session is re-checked with the fixed
script after the queue finishes (`.recheck/`); the report uses the re-check.
