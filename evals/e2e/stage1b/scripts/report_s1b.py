#!/usr/bin/env python3
"""stage1b/runs -> stage1b/runs/_extract.json + stage1b/report-1b.md (numbers only). Run after blind judging."""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import yaml

E2E = Path(__file__).resolve().parents[2]
S1B = E2E / "stage1b"
sys.path.insert(0, str(E2E / "scripts"))
import extract as ex  # noqa: E402
import extract05 as ex05  # noqa: E402

TASKS = yaml.safe_load((S1B / "tasks-1b.yaml").read_text())["tasks"]
TD = {t["id"]: t for t in TASKS}


def tool_events(path):
    """[(tool_name, input)] in order, main thread only."""
    out = []
    for line in path.read_text().splitlines():
        e = json.loads(line)
        if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
            for c in e["message"]["content"]:
                if c["type"] == "tool_use":
                    out.append((c["name"], c["input"]))
    return out


def first_idx(ev, pred):
    return next((i for i, (n, inp) in enumerate(ev) if pred(n, inp)), None)


def is_edit(n):
    return n in ("Write", "Edit", "MultiEdit", "NotebookEdit")


def extract():
    rows = []
    for cond in ("A", "B", "C", "C2"):
        runs = S1B / "runs" / cond
        if not runs.is_dir():
            continue
        ex.RUNS = runs
        for mp in sorted(runs.glob("*.meta.json")):
            meta = json.loads(mp.read_text())
            name = mp.name[: -len(".meta.json")]
            t = dict(TD[meta["task"]["id"]], id=name)
            r = ex.extract(t)
            r.pop("meta", None)
            r.update(task_id=meta["task"]["id"], cond=cond, rep=meta["rep"], name=name, check=meta["check"],
                     diff=meta["diff"], blind_code=meta.get("blind_code"), wall_s=meta["session"]["wall_s"],
                     exit_code=meta["session"]["exit_code"], index_built_at=meta.get("index_built_at"))
            r["timing"] = ex05.timing(runs, name, meta["session"]["spawn_epoch_ms"])
            # some sessions emit several result events (follow-up turns after background agents finish):
            # sum turns / duration / tokens over all of them; subtype lists each segment
            res = [json.loads(l) for l in (runs / f"{name}.jsonl").read_text().splitlines() if '"type":"result"' in l]
            if len(res) > 1:
                u = [x.get("usage") or {} for x in res]
                r.update(num_turns=sum(x.get("num_turns") or 0 for x in res),
                         duration_ms=sum(x.get("duration_ms") or 0 for x in res),
                         output_tokens=sum(x.get("output_tokens") or 0 for x in u),
                         input_tokens_total=sum((x.get("input_tokens") or 0) + (x.get("cache_creation_input_tokens") or 0)
                                                + (x.get("cache_read_input_tokens") or 0) for x in u),
                         result_subtype=res[0].get("subtype") + f" (+{len(res)-1} follow-up)",
                         final_text=res[-1].get("result"), total_cost_usd=res[-1].get("total_cost_usd"))
            r["result_events"] = len(res)
            ev = tool_events(runs / f"{name}.jsonl")
            fp = lambda inp: str(inp.get("file_path") or inp.get("notebook_path") or "")  # noqa: E731
            if r["task_id"] == "s1b-fa-tags-plan":
                ip = first_idx(ev, lambda n, i: is_edit(n) and fp(i).endswith("PLAN.md"))
                ic = first_idx(ev, lambda n, i: is_edit(n) and not fp(i).endswith("PLAN.md"))
                r["plan_first"] = {"plan_edit_idx": ip, "first_code_edit_idx": ic,
                                   "plan_before_code": ip is not None and (ic is None or ip < ic)}
            if r["task_id"] == "s1b-fa-utils-tests":
                it = first_idx(ev, lambda n, i: is_edit(n) and "/tests/" in fp(i))
                isrc = first_idx(ev, lambda n, i: is_edit(n) and "/backend/app/" in fp(i))
                r["test_first"] = {"first_test_edit_idx": it, "first_app_edit_idx": isrc,
                                   "test_before_app_edit": it is not None and (isrc is None or it < isrc),
                                   "app_edited": isrc is not None}
            r["final_chars"] = len(r.get("final_text") or "")
            if cond in ("C", "C2"):
                exp = [x.split("@")[0] for x in TD[r["task_id"]]["expert_skills"]]
                top = [x["id"].split("@")[0] for x in json.loads(r["search_calls"][0]["result"])["results"]] if r["search_calls"] else []
                r["expert_in_top10"] = {e: (top.index(e) + 1 if e in top[:10] else None) for e in exp}
                r["search_top10"] = top[:10]
                # every search_skills call: k asked for, results returned, expert's rank among them
                r["searches"] = []
                for call in r["search_calls"]:
                    try:
                        ids = [x["id"].split("@")[0] for x in json.loads(call["result"])["results"]]
                    except Exception:
                        ids = []
                    inp = call.get("input") or {}
                    r["searches"].append({"query": inp.get("query"), "k": inp.get("k"), "verbose": inp.get("verbose"),
                                          "returned": len(ids), "result_chars": len(call.get("result") or ""),
                                          "expert_rank": {e: (ids.index(e) + 1 if e in ids else None) for e in exp}})
            rows.append(r)
    (S1B / "runs" / "_extract.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    return rows


def med(v):
    v = [x for x in v if isinstance(x, (int, float))]
    return st.median(v) if v else None


def f(x, d=0):
    if isinstance(x, float) and d == 0 and x != int(x):
        d = 1  # a median of an even count (19.5) is not rounded to 20
    return "-" if x is None else f"{x:,.{d}f}"


def short(i):
    return i.rstrip("/").rsplit("/", 1)[-1] + "(local)" if i.startswith("path:") else i.split("@")[0]


def report(rows, conds="ABC", out_name="report-1b.md", title="# skillfetch 1b — 5태스크 × A/B/C × 2회 (report)",
           header="report-header.md", blind_dir=None):
    conds = list(conds)
    blind_dir = blind_dir or S1B
    by = defaultdict(list)
    for r in rows:
        by[(r["task_id"], r["cond"])].append(r)
    for v in by.values():
        v.sort(key=lambda x: x["rep"])
    L = []
    w = L.append
    w(title)
    w("")
    hdr = S1B / header
    if hdr.exists():
        w(hdr.read_text().rstrip())
        w("")
    w("## 1. 조건별 집계")
    w("")
    w("| 태스크 | 조건 | check pass | 중앙 턴 | 중앙 입력 토큰 | 중앙 출력 토큰 | 중앙 시간 s | error_max_turns |")
    w("|---|---|---|---|---|---|---|---|")
    for t in TASKS:
        for c in conds:
            rr = by[(t["id"], c)]
            w(f"| {t['id']} | {c} | {sum(1 for r in rr if r['check'].get('pass') is True)}/{len(rr)} | {f(med([r['num_turns'] for r in rr]))} | "
              f"{f(med([r['input_tokens_total'] for r in rr]))} | {f(med([r['output_tokens'] for r in rr]))} | "
              f"{f(med([(r['duration_ms'] or 0)/1000 for r in rr]))} | {sum(1 for r in rr if str(r['result_subtype']).startswith('error_max_turns'))} |")
    w("")
    for c in conds:
        rr = [r for r in rows if r["cond"] == c]
        w(f"- {c} 전체: check pass {sum(1 for r in rr if r['check'].get('pass') is True)}/{len(rr)}, 중앙 턴 {f(med([r['num_turns'] for r in rr]))}, "
          f"중앙 입력 {f(med([r['input_tokens_total'] for r in rr]))}, 중앙 출력 {f(med([r['output_tokens'] for r in rr]))}")
    w("")
    w("## 2. C: 전문가 스킬의 search 순위, 실제 로드")
    w("")
    w("순위 = 세션이 받은 search_skills 결과 목록 안의 순위(C는 k=10, C2는 기본 k=50). 결과 크기 = 도구 결과 문자 수 / 4.")
    w("")
    w("| 태스크 | 조건 | run | search | query | k / 받은 수 / 결과 크기 | 전문가 스킬 순위 | 로드한 스킬 | load 토큰 | MCP ready s | 첫 skillfetch 호출 s |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for t in TASKS:
        for c in [x for x in conds if x.startswith("C")]:
            for r in by[(t["id"], c)]:
                q = "; ".join(x["input"].get("query", "") for x in r["search_calls"]).replace("|", "/")
                ss = r.get("searches") or []
                kk = "; ".join(f"{x['k'] or 'default'} / {x['returned']} / {f(x['result_chars'] / 4)}" for x in ss) or "-"
                e = "; ".join(", ".join(f"`{k}` {('#' + str(v)) if v else '없음'}" for k, v in x["expert_rank"].items()) for x in ss) or "search 안 함"
                w(f"| {t['id']} | {c} | r{r['rep']} | {'Y' if r['search_calls'] else 'N'} ({r['chain']}) | {q or '-'} | {kk} | {e} | "
                  f"{', '.join('`'+short(i)+'`' for i in r['loaded_ids']) or '-'} | {f(r['load_tokens_reported']) if r['load_tokens_reported'] else '-'} | "
                  f"{f((r['timing'].get('mcp_ready_ms') or 0)/1000, 1)} | {f((r['timing'].get('first_sf_call_ms') or 0)/1000, 1) if r['timing'].get('first_sf_call_ms') else '-'} |")
    w("")
    w("## 3. 태스크별 측정")
    w("")
    w("### s1b-fa-tags-plan — PLAN.md를 코드보다 먼저 썼나 (세션 로그의 Write/Edit 순서)")
    w("")
    w("| 조건 | run | PLAN.md 경로 | PLAN.md 편집 순번 | 첫 코드 편집 순번 | 플랜 먼저 | check | 실패 항목 |")
    w("|---|---|---|---|---|---|---|---|")
    for c in conds:
        for r in by[("s1b-fa-tags-plan", c)]:
            pf = r["plan_first"]
            w(f"| {c} | r{r['rep']} | {r['check'].get('info', {}).get('plan_paths')} | {pf['plan_edit_idx']} | {pf['first_code_edit_idx']} | "
              f"{'Y' if pf['plan_before_code'] else 'N'} | {r['check'].get('pass')} | {', '.join(i['name'] for i in r['check'].get('items', []) if i.get('pass') is False) or '-'} |")
    w("")
    w("### s1b-fa-service — 최종 응답 길이와 출력 토큰 (\"간결하게\" 없음)")
    w("")
    w("| 조건 | run | 최종 응답 문자 수 | 출력 토큰 | 턴 | check | items.py 직접 DB 호출 수 | items.py 줄 수 |")
    w("|---|---|---|---|---|---|---|---|")
    for c in conds:
        for r in by[("s1b-fa-service", c)]:
            info = r["check"].get("info", {})
            w(f"| {c} | r{r['rep']} | {f(r['final_chars'])} | {f(r['output_tokens'])} | {r['num_turns']} | {r['check'].get('pass')} | "
              f"{info.get('items_py_direct_db_calls')} | {info.get('items_py_lines')} |")
    for c in conds:
        rr = by[("s1b-fa-service", c)]
        w(f"- {c}: 최종 응답 문자 수 중앙 {f(med([r['final_chars'] for r in rr]))}, 출력 토큰 중앙 {f(med([r['output_tokens'] for r in rr]))}")
    w("")
    w("### s1b-fa-utils-tests — 커버리지 전/후, 테스트 먼저")
    w("")
    w("app/utils.py 업스트림 커버리지(전체 스위트) 89.06%.")
    w("")
    w("| 조건 | run | 커버리지 후 (전체 스위트) | 새 테스트만 | 새 테스트 파일 | 테스트 편집이 app 편집보다 먼저 | app 수정 여부 | check |")
    w("|---|---|---|---|---|---|---|---|")
    for c in conds:
        for r in by[("s1b-fa-utils-tests", c)]:
            info, tf = r["check"].get("info", {}), r["test_first"]
            w(f"| {c} | r{r['rep']} | {info.get('utils_coverage_suite')}% | {info.get('utils_coverage_new-only')}% | {info.get('new_test_files')} | "
              f"{'Y' if tf['test_before_app_edit'] else 'N'} | {'Y' if tf['app_edited'] else 'N'} | {r['check'].get('pass')} |")
    w("")
    w("### 랜딩 2태스크 — 자동 체크")
    w("")
    w("| 태스크 | 조건 | run | check | 실패 항목 | 라우트 |")
    w("|---|---|---|---|---|---|")
    for tid in ("s1b-nx-landing", "s1b-fa-landing"):
        for c in conds:
            for r in by[(tid, c)]:
                w(f"| {tid} | {c} | r{r['rep']} | {r['check'].get('pass')} | {', '.join(i['name'] for i in r['check'].get('items', []) if i.get('pass') is False) or '-'} | "
                  f"{r['check'].get('info', {}).get('route', '/landing')} |")
    w("")
    w("## 4. 블라인드 판정 (판정자 1명, unblind 후)")
    w("")
    brp = Path(blind_dir) / "blind-ranking-results.md"
    br = brp.read_text() if brp.exists() else ""
    agg = [l for l in br.split("# 조건별 집계 (평균)")[-1].splitlines() if l.startswith("| blind-ranking.md |") and "| 전체 " not in l]
    if agg:
        w("| 세트 | 지표 | 조건별 평균 (n) |")
        w("|---|---|---|")
        for l in agg:
            c = [x.strip() for x in l.strip("|").split("|")]
            w(f"| {c[1]} | {c[2]} | {c[3]} |")
        w("")
        w("세트별 코드·조건·점수와 판정 근거: `blind-ranking-results.md`, `blind-ranking.md`. 랜딩 두 세트는 순위·점수를 함께 `screens` 묶음으로 집계(n=4/조건).")
    w("")
    w("## 5. 세션별 전체")
    w("")
    w("| 태스크 | 조건 | run | subtype | 턴 | 입력 토큰 | 출력 토큰 | 시간 s | diff 파일 수 | check |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for t in TASKS:
        for c in conds:
            for r in by[(t["id"], c)]:
                w(f"| {t['id']} | {c} | r{r['rep']} | {r['result_subtype']} | {r['num_turns']} | {f(r['input_tokens_total'])} | {f(r['output_tokens'])} | "
                  f"{f((r['duration_ms'] or 0)/1000)} | {len(r['diff']['files'])} | {r['check'].get('pass')} |")
    (S1B / out_name).write_text("\n".join(L) + "\n")
    print("wrote", S1B / out_name, len(L))


if __name__ == "__main__":
    report(extract())
