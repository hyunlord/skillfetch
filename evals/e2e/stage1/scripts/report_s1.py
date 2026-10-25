#!/usr/bin/env python3
"""stage1/runs/_extract.json -> stage1/report-stage1.md. Numbers only; no judgments."""
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import yaml

S1 = Path(__file__).resolve().parents[1]
R = json.loads((S1 / "runs" / "_extract.json").read_text())
TASKS = yaml.safe_load((S1 / "tasks-stage1.yaml").read_text())["tasks"]
COND_DESC = {
    "A": "skillfetch 없음 (업스트림 트리, 레포 내장 fastapi/sqlmodel 스킬은 그대로)",
    "B": "A + 전문가 스킬(`expert-skills.md` id를 pinned로 resolve_set/load_skills 한 출력)을 `--append-system-prompt-file`로 주입",
    "C": "A + 머지된 라우터 스킬 + 프로젝트 `.mcp.json`(skillfetch). 로컬 스킬 `path:` pin 허용",
}


def med(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return st.median(v) if v else None


def mean(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return sum(v) / len(v) if v else None


def f0(x, d=0):
    return "-" if x is None else (f"{x:,.{d}f}")


def check_pass(r):
    return r["check"].get("pass")


def failed_items(r):
    return [i["name"] for i in r["check"].get("items", []) if i.get("pass") is False]


def na_items(r):
    return [i["name"] for i in r["check"].get("items", []) if i.get("pass") is None]


def clean_diff(r):
    """diff vs base minus env noise (.omc/, graft's .gitignore block and .ignore); lockfiles separate."""
    import re
    patch = (S1 / "runs" / r["cond"] / f"{r['name']}.diff").read_text()
    add = dele = la = ld = 0
    graft = {"+", "+# graft's local graph cache — regenerable, not committed (run `graft build`).", "+/graft/"}
    for ch in re.split(r"(?=^diff --git )", patch, flags=re.M):
        if not ch.startswith("diff --git"):
            continue
        m = re.match(r"diff --git a/(.*?) b/(.*)$", ch.split("\n", 1)[0])
        path = m.group(2) if m else ""
        if "/.omc/" in "/" + path or path == ".ignore":
            continue
        body = [l for l in ch.split("\n") if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        if path == ".gitignore":
            body = [l for l in body if l not in graft]
        a = sum(1 for l in body if l.startswith("+"))
        d = sum(1 for l in body if l.startswith("-"))
        if path.endswith(("package-lock.json", "uv.lock", "bun.lock")):
            la, ld = la + a, ld + d
        else:
            add, dele = add + a, dele + d
    return add, dele, la, ld


def short(sid):
    return sid.rstrip("/").rsplit("/", 1)[-1] + "(local)" if sid.startswith("path:") else sid.split("@")[0]


def main():
    L = []
    w = L.append
    by = defaultdict(list)
    for r in R:
        by[(r["task_id"], r["cond"])].append(r)
    for v in by.values():
        v.sort(key=lambda x: x["rep"])
    expert_tasks = [t["id"] for t in TASKS if t.get("expert_skills")]
    none_tasks = [t["id"] for t in TASKS if not t.get("expert_skills")]

    w("# skillfetch 1단계 — 3조건 비교 (report)")
    w("")
    w(open(S1 / "report-header.md").read().rstrip() if (S1 / "report-header.md").exists() else "")
    w("")
    w("## 조건")
    w("")
    for c, d in COND_DESC.items():
        w(f"- **{c}**: {d}")
    w("")

    # aggregates
    w("## 1. 조건별 집계")
    w("")
    for label, ids, conds in (("전문가 스킬이 있는 15개 태스크 (A/B/C, 각 2회)", expert_tasks, ("A", "B", "C")),
                              ("전문가 스킬이 없는 5개 태스크 (A/C, 각 2회)", none_tasks, ("A", "C")),
                              ("전체 20개 태스크 (A/C, 각 2회)", expert_tasks + none_tasks, ("A", "C"))):
        w(f"### {label}")
        w("")
        w("| 조건 | 세션 | check pass | check fail | check 없음/오류 | 중앙 턴 | 평균 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 duration s | 중앙 diff +/- (정제, lockfile 제외) | error_max_turns |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for c in conds:
            rows = [r for t in ids for r in by[(t, c)]]
            p = sum(1 for r in rows if check_pass(r) is True)
            f = sum(1 for r in rows if check_pass(r) is False)
            n = len(rows) - p - f
            w(f"| {c} | {len(rows)} | {p} | {f} | {n} | {f0(med([r['num_turns'] for r in rows]))} | {f0(mean([r['num_turns'] for r in rows]),1)} | "
              f"{f0(med([r['input_tokens_total'] for r in rows]))} | {f0(med([r['output_tokens'] for r in rows]))} | "
              f"{f0(med([r['duration_ms']/1000 for r in rows if r['duration_ms']]))} | "
              f"{f0(med([clean_diff(r)[0] for r in rows]))}/{f0(med([clean_diff(r)[1] for r in rows]))} | "
              f"{sum(1 for r in rows if r['result_subtype']=='error_max_turns')} |")
        w("")
    w("### 종류별 check pass (세션 수 기준)")
    w("")
    w("| 종류 | 태스크 수 | A | B (전문가 있는 태스크만) | C |")
    w("|---|---|---|---|---|")
    for k in ("feature", "refactor", "test", "bugfix", "docs"):
        ids = [t["id"] for t in TASKS if t["kind"] == k]
        cells = []
        for c in ("A", "B", "C"):
            rows = [r for t in ids for r in by[(t, c)]]
            cells.append(f"{sum(1 for r in rows if check_pass(r) is True)}/{len(rows)}" if rows else "-")
        w(f"| {k} | {len(ids)} | " + " | ".join(cells) + " |")
    w("")
    rows_c = [r for r in R if r["cond"] == "C"]
    fired = [r for r in rows_c if r["search_calls"]]
    w("### C: skillfetch 사용")
    w("")
    w(f"- `search_skills` 호출 세션: {len(fired)}/{len(rows_c)}; search→resolve→load 완주: {sum(1 for r in fired if r['chain']=='search+resolve+load')}; search만: {sum(1 for r in fired if r['chain']=='search')}")
    w(f"- 로드 스킬 수(완주 세션) 중앙 {f0(med([len(r['loaded_ids']) for r in fired if r['loaded_ids']]))}, load 토큰 중앙 {f0(med([r['load_tokens_reported'] for r in fired if r['load_tokens_reported']]))}")
    w(f"- 로컬 `path:` pin 포함 세션: {sum(1 for r in fired if any(i.startswith('path:') for i in r['loaded_ids']))}")
    w(f"- MCP ready (spawn 기준) 중앙 {f0(med([r['timing'].get('mcp_ready_ms')/1000 for r in rows_c if r['timing'].get('mcp_ready_ms')]),1)}s, 범위 "
      f"{f0(min([r['timing']['mcp_ready_ms']/1000 for r in rows_c if r['timing'].get('mcp_ready_ms')] or [0]),1)}–{f0(max([r['timing']['mcp_ready_ms']/1000 for r in rows_c if r['timing'].get('mcp_ready_ms')] or [0]),1)}s; 연결 실패 {sum(1 for r in rows_c if r['timing'].get('mcp_fail'))}")
    kinds = {t["id"]: (t["kind"], t["lang"]) for t in TASKS}
    w("- 종류별 search 호출: " + ", ".join(f"{k} {sum(1 for r in fired if kinds[r['task_id']][0]==k)}/{sum(1 for r in rows_c if kinds[r['task_id']][0]==k)}" for k in ("feature", "refactor", "test", "bugfix", "docs"))
      + "; 언어별: " + ", ".join(f"{lg} {sum(1 for r in fired if kinds[r['task_id']][1]==lg)}/{sum(1 for r in rows_c if kinds[r['task_id']][1]==lg)}" for lg in ("en", "ko")))
    w("- search 미호출 C 세션: " + ", ".join(r["name"] for r in rows_c if not r["search_calls"]))
    w(f"- B 주입 토큰(전문가 세트 token_estimate 합) 중앙 {f0(med([r['expert_tokens'] for r in R if r['cond']=='B']))}")
    w("")

    re_rows = [r for r in R if r.get("check_original") is not None]
    changed = [r for r in re_rows if r["check_original"].get("pass") != r["check"].get("pass")]
    w(f"### 재검사 (`<E2 plugin>` 제거 후)")
    w("")
    w(f"- 재검사 세션 {len(re_rows)}개, 판정 변경 {len(changed)}개: " + (", ".join(f"{r['cond']} {r['name']} ({r['check_original'].get('pass')} → {r['check'].get('pass')})" for r in changed) or "없음"))
    w(f"- `<E2 plugin>/`가 지워진 세션(체크 직전): {sum(1 for r in R if r['check'].get('env_noise_removed'))}/{len(R)}")
    w("")

    # per task
    w("## 2. 태스크별 상세")
    w("")
    for t in TASKS:
        w(f"### {t['id']} — {t['kind']}/{t['lang']}{' (UI)' if t.get('ui') else ''}")
        w("")
        w(f"> {t['prompt']}")
        w("")
        w(f"전문가 스킬(B): {', '.join('`'+x.split('@')[0]+'`' for x in t.get('expert_skills') or []) or '없음 → A/C만'}")
        w("")
        w("| 조건 | rep | check | 실패 항목 | N/A 항목 | 턴 | 입력 토큰 | 출력 토큰 | duration s | diff +/- | subtype | C: search query | C: 로드 스킬 | C: load 토큰 | C: MCP ready s | C: 첫 skillfetch 호출 s |")
        w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
        for c in ("A", "B", "C"):
            for r in by[(t["id"], c)]:
                q = "; ".join(x["input"].get("query", "") for x in r["search_calls"]) if c == "C" else ""
                ld = ", ".join("`" + short(i) + "`" for i in r["loaded_ids"]) if c == "C" else ""
                cp = check_pass(r)
                w(f"| {c} | {r['rep']} | {'pass' if cp is True else 'fail' if cp is False else 'n/a: ' + str(r['check'].get('error',''))} | "
                  f"{', '.join(failed_items(r)) or '-'} | {', '.join(na_items(r)) or '-'} | {r['num_turns']} | {f0(r['input_tokens_total'])} | {f0(r['output_tokens'])} | "
                  f"{f0((r['duration_ms'] or 0)/1000)} | +{clean_diff(r)[0]}/-{clean_diff(r)[1]}{' (lock +%d/-%d)' % clean_diff(r)[2:] if any(clean_diff(r)[2:]) else ''} | {r['result_subtype']} | "
                  f"{q.replace('|', '/') if c == 'C' else ''} | {ld if c == 'C' else ''} | {f0(r['load_tokens_reported']) if c == 'C' and r['load_tokens_reported'] else ('-' if c == 'C' else '')} | "
                  f"{f0((r['timing'].get('mcp_ready_ms') or 0)/1000,1) if c == 'C' else ''} | {f0((r['timing'].get('first_sf_call_ms') or 0)/1000,1) if c == 'C' and r['timing'].get('first_sf_call_ms') else ('-' if c == 'C' else '')} |")
        vis = sorted({r['blind_code'] for c in ('A', 'B', 'C') for r in by[(t['id'], c)] if r.get('blind_code')})
        if vis:
            w("")
            w(f"블라인드 스크린샷: `screens-blind/{t['id']}/` ({len(vis)}개 폴더, 조건 매핑은 `screens-key.jsonl`)")
        w("")
    (S1 / "report-stage1.md").write_text("\n".join(L) + "\n")
    print("wrote report-stage1.md", len(L))


if __name__ == "__main__":
    main()
