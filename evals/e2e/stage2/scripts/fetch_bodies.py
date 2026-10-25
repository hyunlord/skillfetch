"""Fetch (hash-verified) bodies of B candidates into search/bodies/<name>.md via resolve_set + load_skills.
usage: uvx --from git+https://github.com/hyunlord/skillfetch@e2a1b65 python scripts/fetch_bodies.py <id> ..."""
import sys
from pathlib import Path

from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S2 = Path(__file__).resolve().parents[1]
s = Session(Index.load(DEFAULT_INDEX_DIR))
for sid in sys.argv[1:]:
    r = s.resolve_set([], [sid])
    out = s.load_skills(r["set_id"], max_tokens=20000)
    name = sid.split("/")[1].split("@")[0]
    (S2 / "search" / "bodies" / f"{name}.md").write_text(out["content"])
    print(sid, [x["token_estimate"] for x in out["skills"]], out["errors"])
