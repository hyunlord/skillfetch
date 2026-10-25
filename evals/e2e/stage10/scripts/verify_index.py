#!/usr/bin/env python3
"""Write-once check: every index copy file still matches stage10/index/HASHES.sha256 (recorded at the pre-check), no file
added or removed. Exit 1 (and print the differences) otherwise. Called before every queue, every session and judging."""
import hashlib
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "index"
want = {}
for line in (D / "HASHES.sha256").read_text().splitlines():
    h, p = line.split(None, 1)
    want[p.strip()] = h
have = {str(f.relative_to(D)): hashlib.sha256(f.read_bytes()).hexdigest() for d in ("release", "staging-4") for f in sorted((D / d).iterdir())}
bad = sorted(set(want) ^ set(have)) + sorted(p for p in want if p in have and want[p] != have[p])
if bad:
    print("INDEX CHANGED:", bad)
    sys.exit(1)
print(f"index ok ({len(have)} files)")
