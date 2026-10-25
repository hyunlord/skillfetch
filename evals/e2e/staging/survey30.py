"""Stage-8 top-30 staging survey (no extraction): per repository, SKILL.md files, discovered
skills, lint / injection-scan pass, content_hash already in the index or earlier in the list,
licenses (root LICENSE + per-skill)."""
import collections, json, os, subprocess, sys
from pathlib import Path
from skillfetch.ingest.build import _record
from skillfetch.ingest.extract import MAX_SKILL_TOKENS
from skillfetch.ingest.licenses import LICENSE_FILES, classify_text
from skillfetch.ingest.skillfile import SKILL_FILE, discover_skills
from skillfetch.ingest.snapshot import Snapshot
from skillfetch.ingest.sources import Source

W = Path("~/.skillfetch/work-staging").expanduser()
EXCLUDE = ["template", "templates", "fixtures", "__fixtures__", "testdata", "test-fixtures"]
cands = json.load(open(Path("<e2e>/stage8/source-candidates.json").expanduser()))[:30]
index_hashes = {json.loads(l)["content_hash"] for l in open("data/index/skills.jsonl")}
index_hashes |= {json.loads(l)["content_hash"] for l in open("data/index/rejected.jsonl")}
seen = set()
rows = []
for rank, c in enumerate(cands, 1):
    repo = c["repo"]; d = W / repo.replace("/", "__")
    row = {"rank": rank, "repo": repo, "gap56": c["gap56"], "relevant": c["relevant_skill_names"]}
    if not (d / ".git").is_dir():
        row["error"] = "clone failed"; rows.append(row); continue
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True).stdout.strip()
    all_md = [Path(r) for r, ds, fs in os.walk(d) if ".git" not in Path(r).parts and SKILL_FILE in fs]
    hidden = sum(1 for p in all_md if any(part.startswith(".") for part in p.relative_to(d).parts))
    src = Source(id=repo.replace("/", "__"), kind="dir", url=str(d), exclude=EXCLUDE,
                 publisher=repo.split("/")[0], publisher_trust="unknown")
    snap = Snapshot(src, d, commit, None)
    found = discover_skills(d, EXCLUDE, base=d)
    recs = [_record(snap, s).record for s in found]
    st = collections.Counter(r.status for r in recs)
    ok = [r for r in recs if r.status == "ok"]
    in_index = sum(r.content_hash in index_hashes for r in ok)
    dup_earlier = 0; new = []
    local = set()
    for r in ok:
        if r.content_hash in index_hashes: continue
        if r.content_hash in seen or r.content_hash in local: dup_earlier += 1; continue
        local.add(r.content_hash); new.append(r)
    seen |= {r.content_hash for r in recs}
    root_lic = None
    for name in LICENSE_FILES:
        if (d / name).is_file():
            root_lic = classify_text((d / name).read_text(errors="replace")) or "unrecognised"; break
    lic = collections.Counter((r.license, r.license_origin) for r in new)
    row.update(commit=commit[:12], skill_md=len(all_md), hidden=hidden, discovered=len(found),
               lint_failed=st["lint_failed"], scan_failed=st["scan_failed"], ok=len(ok),
               in_index=in_index, dup=dup_earlier, new=len(new),
               new_too_large=sum(r.token_estimate > MAX_SKILL_TOKENS for r in new),
               new_tokens=sum(r.token_estimate for r in new),
               root_license=root_lic or "none",
               new_license={f"{k[0]} ({k[1]})": v for k, v in lic.most_common()},
               new_redistributable=sum(r.redistributable for r in new))
    rows.append(row)
    print(rank, repo, row["discovered"], row["ok"], row["new"], file=sys.stderr)
json.dump(rows, open(sys.argv[1], "w"), indent=1)
