"""B selection step 1: search_skills top 50 for each stage-2 task sentence, with the repo's profile."""
import json
from pathlib import Path

import yaml
from skillfetch.index.loader import DEFAULT_INDEX_DIR, Index
from skillfetch.mcp.session import Session

S2 = Path(__file__).resolve().parents[1]
s = Session(Index.load(DEFAULT_INDEX_DIR))
print("index", s.index.manifest["built_at"])
for t in yaml.safe_load((S2 / "tasks-stage2.yaml").read_text())["tasks"]:
    prof = s.profile_repo(str(S2.parent / "repos" / t["repo"]))
    res = s.search_skills(t["search_sentence"], prof)
    full = s.search_skills(t["search_sentence"], prof, verbose=True)
    (S2 / "search" / f"{t['id']}.json").write_text(json.dumps({"query": t["search_sentence"], "profile": prof, "compact": res, "verbose": full}, indent=1, ensure_ascii=False))
    print(f"\n## {t['id']} profile={prof.get('tags')}")
    for i, r in enumerate(res["results"], 1):
        print(f"{i:2}. {r['id']} [{r['tier']}] {r['token_estimate']} — {r['summary'][:110]}")
