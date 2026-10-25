#!/usr/bin/env python3
"""Step 2a input: catalog.md = one line per canonical tier A/B skill (the set search_skills can return):
`<id> | <title> | <10-word summary>`. The 10 words are the summary's first words after stripping boilerplate
openers ("Guides the agent to", "Use ... to", "Helps", "Provides") that carry no content."""
import json
import re
from pathlib import Path

S3 = Path(__file__).resolve().parents[1]
LEAD = re.compile(r"^(?:(?:guides?|helps?|directs?|instructs?|teaches|enables|assists?|requires?|tells?|lets?)\s+"
                  r"(?:the\s+)?(?:agent|agents|developers?|users?|claude|ai\s+agents?)?\s*(?:to|through|in|on|with|when|by)?\s+|"
                  r"provides?\s+|use\s+(?:this\s+skill\s+)?(?:to\s+)?|this\s+skill\s+)", re.I)


def ten(summary):
    s = " ".join(str(summary or "").split())
    s = LEAD.sub("", s, count=1)
    words = s.split()
    return " ".join(words[:10]).rstrip(",;:.") + ("…" if len(words) > 10 else "")


recs = [json.loads(l) for l in (Path.home() / ".skillfetch/index/skills.jsonl").open()]
can = [r for r in recs if r.get("canonical_id", r["id"]) == r["id"] and r.get("tier") in ("A", "B")]
lines = [f"{r['id']} | {r.get('title') or r['name']} | {ten(r.get('summary') or r.get('description'))}" for r in can]
(S3 / "gen" / "catalog.md").write_text("\n".join(lines) + "\n")
print(len(lines), "skills;", len("\n".join(lines)) // 4, "tokens (chars/4)")
print("\n".join(lines[:8]))
