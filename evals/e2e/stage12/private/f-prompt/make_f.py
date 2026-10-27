#!/usr/bin/env python3
"""Stage 12b F prompt (stage12b/DESIGN.md §1.3): all 24 Northwind bodies in the load_skills section format
(`## <n>. <title> (<id>)`, blank line, body; sections joined by a blank line), index-nw order (id ascending), no conflict
resolution. Body = read_skill(<skill folder>).body_lines joined and stripped, title = the index title (as load_skills).
usage: uvx --from ~/skillfetch-e2e-wt/s26-server/c55d561 python make_f.py  -> F.md"""
import hashlib
import json
from pathlib import Path

from skillfetch.ingest.skillfile import content_hash, read_skill

HERE = Path(__file__).resolve().parent
PRIV = HERE.parent
recs = sorted((r for r in map(json.loads, (PRIV / "index-nw" / "skills.jsonl").open()) if r["id"].startswith("northwind/")),
              key=lambda r: r["id"])
assert len(recs) == 24
sections = []
for r in recs:
    folder = PRIV / "northwind-skills" / r["id"].split("/", 1)[1].split("@")[0]
    assert content_hash(folder) == r["content_hash"], r["id"]
    doc = read_skill(folder)
    body = "\n".join(doc.body_lines).strip()
    title = r.get("title") or (doc.frontmatter or {}).get("name") or r["id"]
    sections.append(f"## {len(sections) + 1}. {title} ({r['id']})\n\n{body}")
text = "\n\n".join(sections)
(HERE / "F.md").write_text(text)
print(len(sections), "sections", len(text) // 4, "tokens est", hashlib.sha256(text.encode()).hexdigest())
