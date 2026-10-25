#!/usr/bin/env python3
"""Unblind a ranking and aggregate by condition.

  python3 stage1/scripts/unblind_ranking.py --template   # writes stage1/blind-ranking.template.md (codes only)
  python3 stage1/scripts/unblind_ranking.py --validate [file ...]  # format check only, never reads the key files
  python3 stage1/scripts/unblind_ranking.py [file ...]    # default stage1/blind-ranking.md -> blind-ranking-results.md

Ranking file format, one section per blind set:
  `## <set>`  — <set> is a folder under screens-blind/ (`## s1-fa-03`) or docs-blind/ (`## docs/s1-fa-10`)
  rank lines  — `1. <code>` (1 = best; ties: same number, or `2. <code>, <code>`); every code of the set exactly once
  score table — optional markdown table whose first column is the code; every numeric column is aggregated per
                condition by its header (e.g. `(a) AI느낌 수`, `(b) 쓸만함 1-5`, `머지 1-5`). Other text is ignored.
Several files (judges) can be passed; results are reported per file and pooled. The key files are read only
after every file validates, so nothing is revealed for a partial or wrong file.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

S1 = Path(__file__).resolve().parents[1]
if "--root" in sys.argv:  # e.g. --root stage1b
    _i = sys.argv.index("--root")
    S1 = Path(sys.argv[_i + 1]).resolve()
    del sys.argv[_i:_i + 2]
SETS = [("", S1 / "screens-blind", S1 / "screens-key.jsonl", "dir"),
        ("docs/", S1 / "docs-blind", S1 / "docs-key.jsonl", "md"),
        ("plans/", S1 / "plans-blind", S1 / "plans-key.jsonl", "dir")]
PLAN_COLS = ["단계 구체성 1-5", "파일 명시 1-5", "리스크 1-5", "검증 방법 1-5", "순서 1-5", "플랜 준수 1-5"]


def blind_sets():
    out = {}
    for prefix, root, _key, kind in SETS:
        if root.exists():
            for d in sorted(p for p in root.iterdir() if p.is_dir()):
                codes = [c.name for c in d.iterdir() if c.is_dir()] if kind == "dir" else [c.stem for c in d.glob("*.md")]
                out[prefix + d.name] = sorted(codes)
    return out


def keys():
    m = {}
    for prefix, _root, key, _kind in SETS:
        if key.exists():
            for line in key.read_text().splitlines():
                if line.strip():
                    k = json.loads(line)
                    m[(prefix + k["task"], k["code"])] = (k["cond"], k["rep"])
    return m


def write_template():
    L = ["# blind ranking", "",
         "세트마다: 점수 표를 채우고, 순위 줄의 `?`를 순위 숫자로 바꾼다 (1 = 최고, 동순위 허용, 줄 순서 자유).",
         "코드 순서는 hex 정렬이며 조건과 무관하다. 표/순위 줄 외의 텍스트는 집계에 쓰이지 않는다.", ""]
    for s, codes in blind_sets().items():
        L += [f"## {s}", ""]
        if s.startswith("docs/"):
            L += ["| code | 머지 1-5 | 근거 |", "|---|---|---|"] + [f"| {c} |  |  |" for c in codes]
        elif s.startswith("plans/"):
            L += ["| code | " + " | ".join(PLAN_COLS) + " | 근거 |", "|---|" + "---|" * (len(PLAN_COLS) + 1)] + \
                 [f"| {c} |" + "  |" * (len(PLAN_COLS) + 1) for c in codes]
        else:
            L += ["| code | (a) AI느낌 수 | (b) 쓸만함 1-5 | 근거 |", "|---|---|---|---|"] + [f"| {c} |  |  |  |" for c in codes]
        L += [""] + [f"?. {c}" for c in codes] + [""]
    (S1 / "blind-ranking.template.md").write_text("\n".join(L))
    print("wrote", S1 / "blind-ranking.template.md")


def parse(text, sets):
    ranks, scores, cur, header = defaultdict(dict), defaultdict(dict), None, None
    for line in text.splitlines():
        h = re.match(r"^##\s+(\S+)", line)
        if h:
            cur, header = h.group(1), None
            continue
        if cur is None:
            continue
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] == "code":
                header = cells
            elif header and cells and cells[0] in sets.get(cur, []):
                for name, val in zip(header[1:], cells[1:]):
                    if re.fullmatch(r"-?\d+(\.\d+)?", val):
                        scores[cur].setdefault(cells[0], {})[name] = float(val)
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.+)$", line)
        if m:
            for code in re.split(r"[,\s]+", m.group(2).strip()):
                if code:
                    if code in ranks[cur]:
                        sys.exit(f"{cur}: code {code} listed twice")
                    ranks[cur][code] = int(m.group(1))
    return ranks, scores


def main():
    if "--template" in sys.argv:
        return write_template()
    validate_only = "--validate" in sys.argv
    files = [Path(a) for a in sys.argv[1:] if not a.startswith("--")] or [S1 / "blind-ranking.md"]
    sets = blind_sets()
    parsed = []
    for src in files:  # validate everything before reading any key
        if not src.exists():
            sys.exit(f"missing {src} (start from blind-ranking.template.md)")
        ranks, scores = parse(src.read_text(), sets)
        for s, r in ranks.items():
            if s not in sets:
                sys.exit(f"{src.name}: unknown set {s}")
            missing, extra = set(sets[s]) - set(r), set(r) - set(sets[s])
            if missing or extra:
                sys.exit(f"{src.name} {s}: missing {sorted(missing)} unknown {sorted(extra)}")
        unranked = set(sets) - set(ranks)
        parsed.append((src, ranks, scores))
        if validate_only:
            n_scores = sum(len(v) for v in scores.values())
            print(f"{src.name}: OK — {len(ranks)} sets ranked, {n_scores} scored rows" + (f", not ranked: {sorted(unranked)}" if unranked else ""))
    if validate_only:
        return
    key = keys()
    L = ["# blind ranking — unblinded", "",
         f"sources: {', '.join('`'+p.name+'`' for p, _, _ in parsed)}; mapping: key files next to the blind folders in `{S1.name}/`. "
         "1 = best. 정규화 순위 = (rank − 1) / (n − 1), 0 = 최상.", ""]
    pooled = defaultdict(lambda: defaultdict(list))   # (group, metric) -> cond -> values
    for src, ranks, scores in parsed:
        L += [f"# 판정 파일: {src.name}", ""]
        for s, r in ranks.items():
            n = len(r)
            conds = sorted({key[(s, c)][0] for c in r})
            group = s.split("/")[0] + " " if "/" in s else "screens "
            group += "+".join(conds)
            metrics = sorted({m for v in scores.get(s, {}).values() for m in v})
            L += [f"## {s}", "", "| code | 조건 | rep | 순위 | " + " | ".join(metrics) + " |", "|---|---|---|---|" + "---|" * len(metrics)]
            for code, rk in sorted(r.items(), key=lambda x: x[1]):
                cond, rep = key[(s, code)]
                sc = scores.get(s, {}).get(code, {})
                L.append(f"| {code} | {cond} | r{rep} | {rk} | " + " | ".join(f"{sc[m]:g}" if m in sc else "-" for m in metrics) + " |")
                for g in (group, "전체 " + group.split()[0]):
                    pooled[(src.name, g, "순위")][cond].append(rk)
                    pooled[(src.name, g, "정규화 순위")][cond].append((rk - 1) / (n - 1) if n > 1 else 0.0)
                    for m in metrics:
                        if m in sc:
                            pooled[(src.name, g, m)][cond].append(sc[m])
                            pooled[("(모든 판정자)", g, m)][cond].append(sc[m])
                    pooled[("(모든 판정자)", g, "순위")][cond].append(rk)
                    pooled[("(모든 판정자)", g, "정규화 순위")][cond].append((rk - 1) / (n - 1) if n > 1 else 0.0)
            L.append("")
    L += ["# 조건별 집계 (평균)", "", "| 판정 파일 | 세트 묶음 | 지표 | 조건별 평균 (n) |", "|---|---|---|---|"]
    judges = [p.name for p, _, _ in parsed] + (["(모든 판정자)"] if len(parsed) > 1 else [])
    for j in judges:
        for (jj, g, metric) in sorted(k for k in pooled if k[0] == j):
            d = pooled[(jj, g, metric)]
            L.append(f"| {j} | {g} | {metric} | " + ", ".join(f"{c} {sum(v)/len(v):.2f} ({len(v)})" for c, v in sorted(d.items())) + " |")
    (S1 / "blind-ranking-results.md").write_text("\n".join(L) + "\n")
    print("wrote", S1 / "blind-ranking-results.md")


if __name__ == "__main__":
    main()
