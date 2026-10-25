"""Parsers for skillselion-mcp 0.9.11 tool output (search_skillselion, load_skill), and the index lookup used to
merge SS results into our index ids (DESIGN §2-추가 8)."""
import hashlib
import json
import re
import urllib.request
from pathlib import Path

S8 = Path(__file__).resolve().parents[1]
INDEX = Path.home() / ".skillfetch/index/skills.jsonl"


def desc220(s):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= 220 else s[:217] + "..."


def parse_search(text):
    """[{name, repo_line, desc, id}] in rank order; [] for an empty result."""
    out = []
    for blk in re.split(r"^### ", text, flags=re.M)[1:]:
        lines = blk.split("\n")
        m = re.match(r"(.+?)\s+\((skill|mcp|marketplace)\)\s*$", lines[0])
        name = m.group(1).strip() if m else lines[0].strip()
        repo_line = next((l[6:].strip() for l in lines if l.startswith("repo: ")), "")
        sid = re.search(r"load_skill` with id `([^`]+)`", blk)
        body = [l for l in lines[1:] if l.strip() and not re.match(r"(repo|install|load now|details): ", l)
                and not re.match(r"^[\d,]+ (installs|stars)|^\d[\d,]* stars", l)]
        stats = lines[1] if len(lines) > 1 else ""
        desc = next((l for l in body if l != stats), "")
        out.append({"name": name, "repo_line": re.sub(r"^github\.com/", "", repo_line), "desc": desc.strip(),
                    "id": sid.group(1) if sid else None})
    return out


def parse_load(text):
    """{name, repo, folder, switch} or None when nothing was loaded."""
    m = re.match(r"# Skill loaded: (.+?)\s+\(([^)]+)\)", text)
    if not m:
        return None
    f = re.search(r"saved locally → (\S+)", text)
    sw = re.search(r"Or switch to: (.+)", text)
    return {"name": m.group(1).strip(), "repo": m.group(2).strip(), "folder": f.group(1) if f else None,
            "switch": re.findall(r"`([^`]+)`", sw.group(1)) if sw else []}


def id_repo(sid):
    m = re.match(r"skill:([^#]+)#(.*)$", sid or "")  # empty slug = single-skill repo (root SKILL.md)
    return (m.group(1), m.group(2)) if m else (None, None)


def frontmatter_desc(md):
    m = re.match(r"^---\s*\n(.*?)\n---", md, re.S)
    if not m:
        return ""
    fm = m.group(1)
    d = re.search(r"^description:\s*(.*?)(?=^\w[\w-]*:|\Z)", fm, re.S | re.M)
    if not d:
        return ""
    v = d.group(1).strip()
    if v[:1] in ">|":
        v = v[1:]
    return re.sub(r"\s+", " ", v).strip().strip('"').strip("'")


_idx = None


def index():
    """records by id, plus {(owner/repo lower, last path segment lower): [ids]} and {name lower: [ids]}."""
    global _idx
    if _idx is None:
        recs, by_rp, by_name = {}, {}, {}
        for l in INDEX.open():
            r = json.loads(l)
            recs[r["id"]] = r
            m = re.match(r"https://github\.com/([^/]+/[^/]+)/", r.get("source_url") or "")
            seg = (r.get("path") or "").rstrip("/").split("/")[-1] or r["name"]
            if m:
                by_rp.setdefault((m.group(1).lower(), seg.lower()), []).append(r["id"])
            by_name.setdefault(r["name"].lower(), []).append(r["id"])
        _idx = (recs, by_rp, by_name)
    return _idx


def sha(b):
    return hashlib.sha256(b).hexdigest()


_raw_cache = {}


def fetch_skill_md(repo, slug):
    """SKILL.md bytes via raw.githubusercontent (no token), same path order as the client; None if not found."""
    key = (repo, slug)
    if key in _raw_cache:
        return _raw_cache[key]
    cache = S8 / "raw" / "skillmd-fetch"
    cache.mkdir(parents=True, exist_ok=True)
    cf = cache / (re.sub(r"[^\w.-]", "_", f"{repo}#{slug}") + ".json")
    if cf.exists():
        j = json.loads(cf.read_text())
        _raw_cache[key] = j["content"].encode() if j["content"] is not None else None
        return _raw_cache[key]
    paths = [f"skills/{slug}/SKILL.md", f"{slug}/SKILL.md", f".claude/skills/{slug}/SKILL.md", "SKILL.md"] if slug else ["SKILL.md"]
    got = None
    for br in ("main", "master"):
        for p in paths:
            try:
                with urllib.request.urlopen(f"https://raw.githubusercontent.com/{repo}/{br}/{p}", timeout=20) as r:
                    b = r.read()
                if len(b.strip()) > 30:
                    got = (f"{br}/{p}", b)
                    break
            except Exception:
                continue
        if got:
            break
    cf.write_text(json.dumps({"repo": repo, "slug": slug, "path": got[0] if got else None,
                              "content": got[1].decode("utf-8", "replace") if got else None}, ensure_ascii=False))
    _raw_cache[key] = got[1] if got else None
    return _raw_cache[key]
