#!/usr/bin/env python3
"""Build stage14/gallery/stage14-gallery.html (gallery v2 format, three conditions, sessions of six requests) from
stage14-private/gallery-data-14.json (assemble_14.py) and the difference summaries stage14-private/gallery-diffs/<task>.json.
No new sessions. Every summary quote is checked against its source (the run's judge reason or its diff) and the build
stops if one does not match (rule kept from gallery v1/v2).
Page:
  top      the criteria (DESIGN §5) with the D label; session strips (six sessions, one cell per request: task, check, score,
           turns, API-price equivalent, context at the start, skills; the three pilot sessions below, without scores); bar
           charts per task (A / P / R: score, turns, cost) and per position (cost, context at the start); "차이 정리" per
           task; traces of earlier skills ((a) names, (b) files outside the area, (c) judged items)
  task     table of the six outputs; landing: overlay slider per order with a pair switch (P|R, A|P, A|R; desktop and
           mobile); code and docs: the task's core file after the request, side by side A|P and P|R per order (rebuilt by
           replaying the session's diffs), syntax-highlighted, unchanged lines folded; judge reasons, folded
Publication rules as v1/v2 (no user paths or names; skills by name only). usage: build_gallery_14.py"""
import base64
import difflib
import json
import re
import statistics as st
import sys
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(E2E / "stage10" / "gallery"))
sys.path.insert(0, str(E2E / "stageQ" / "gallery"))
sys.path.insert(0, str(E2E / "stage13" / "gallery"))
import build_gallery_s10 as g  # noqa: E402
import build_gallery_v2 as v2  # noqa: E402
import build_gallery_13 as g13  # noqa: E402

OUT = E2E / "stage14" / "gallery" / "stage14-gallery.html"
D = json.loads((E2E / "stage14-private" / "gallery-data-14.json").read_text())
ROWS, SUM, CORES = D["rows"], D["summary"], D["cores"]
DIFFS = {p.stem: json.loads(p.read_text()) for p in (E2E / "stage14-private" / "gallery-diffs").glob("*.json")}
TASKS = ["landing", "api", "apitests", "rust", "docs", "data"]
TNAME = {"landing": "랜딩 페이지", "api": "API 엔드포인트", "apitests": "API 테스트", "rust": "Rust 동시성", "docs": "README 문서", "data": "데이터 스크립트"}
CONDS, ORDERS = ("A", "P", "R"), ("F", "B")
ONAME = {"F": "정순", "B": "역순"}
CNAME = {"A": "A 스킬 없음", "P": "P 인기 스킬 8개 설치", "R": "R 라우터"}
esc, S = v2.esc, g.S


def run(t, c, o):
    return next(r for r in ROWS if r["task"] == t and r["cond"] == c and r["order"] == o)


def run_of(t, label):
    c, o = label.split()
    return run(t, c, o)


def verify_quotes():
    bad = []
    for t, d in DIFFS.items():
        for li in d["lines"]:
            for q in li["quotes"]:
                r = run_of(t, q["run"])
                src = Path(r["diff_path"]).read_text(errors="replace") if q["src"] == "diff" else r.get(f"reason_{q['src']}", "")
                if not q["quote"] or q["quote"] not in src:
                    bad.append(f"{t} | {q['src']} {q['run']} | {q['quote'][:80]}")
    return bad


def num(v, nd=2):
    return "–" if v is None else (f"{v:.{nd}f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


# ---------------------------------------------------------------- charts (rows = labels, three bars each)
def chart(title, unit, labels, vals, vmax, fmtv):
    row, lab, w, pad, bh = 32, 112, 360, 40, 7
    h = len(labels) * row + 34
    bw = w - lab - pad
    ticks = [vmax * i / 4 for i in range(5)]
    out = [f'<figure class="chart"><figcaption>{esc(title)} <span class="sm">{esc(unit)}</span></figcaption>'
           f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">']
    for tv in ticks:
        x = lab + bw * tv / vmax
        out.append(f'<line x1="{x:.1f}" y1="6" x2="{x:.1f}" y2="{h - 22}" class="grid"/><text x="{x:.1f}" y="{h - 8}" class="tick" text-anchor="middle">{fmtv(tv)}</text>')
    for i, (key, name) in enumerate(labels):
        y = 8 + i * row
        out.append(f'<text x="{lab - 6}" y="{y + 15}" class="lab" text-anchor="end">{esc(name)}</text>')
        for j, c in enumerate(CONDS):
            v = vals[key][c]
            yy = y + j * (bh + 1.5)
            ww = max(0.0, min(bw, bw * v / vmax)) if v is not None else 0
            out.append(f'<rect x="{lab}" y="{yy:.1f}" width="{ww:.1f}" height="{bh}" class="b-{c}"><title>{esc(name)} {c} {fmtv(v)}</title></rect>'
                       f'<text x="{lab + ww + 3:.1f}" y="{yy + 6.5:.1f}" class="val">{fmtv(v)}</text>')
    out.append("</svg></figure>")
    return "".join(out)


def charts():
    def per(fn):
        return {t: {c: fn([r for r in ROWS if r["task"] == t and r["cond"] == c]) for c in CONDS} for t in TASKS}
    tl = [(t, TNAME[t]) for t in TASKS]
    score = per(lambda rs: st.mean(r["score"] for r in rs))
    turns = per(lambda rs: st.mean(r["turns"] for r in rs))
    cost = per(lambda rs: st.mean(r["cost"] for r in rs))
    pl = [(k, f"{k}번째 요청") for k in range(1, 7)]
    pcost = {k: {c: st.mean(r["cost"] for r in ROWS if r["k"] == k and r["cond"] == c) for c in CONDS} for k in range(1, 7)}
    pctx = {k: {c: st.mean(r["context_start"] for r in ROWS if r["k"] == k and r["cond"] == c) / 1000 for c in CONDS} for k in range(1, 7)}
    legend = '<p class="legend">' + "".join(f'<span class="sw {c}"></span>{esc(CNAME[c])} ' for c in CONDS) + "</p>"
    f2 = lambda v: "–" if v is None else f"{v:.2f}"  # noqa: E731
    f1 = lambda v: "–" if v is None else (f"{v:.1f}" if v % 1 else f"{v:.0f}")  # noqa: E731
    return legend + '<div class="charts">' + "".join([
        chart("점수", "작업별, (p1+p2)/2, 정순·역순 평균, 1–5", tl, score, 5, f1),
        chart("턴", "작업별, 정순·역순 평균", tl, turns, 45, f1),
        chart("API 단가 환산", "작업별, 요청당 평균, 달러", tl, cost, 7, f2),
        chart("API 단가 환산", "세션 안 위치별, 요청당 평균, 달러", pl, pcost, 7, f2),
        chart("요청 시작 시점 컨텍스트", "위치별 평균, 천 토큰", pl, pctx, 240, f1)]) + "</div>"


# ---------------------------------------------------------------- session strips
def strips():
    out = []
    for c in CONDS:
        for o in ORDERS:
            rs = sorted((r for r in ROWS if r["cond"] == c and r["order"] == o), key=lambda r: r["k"])
            cells = []
            for r in rs:
                chk = '<span class="ok">통과</span>' if r["check"] else '<span class="bad">실패</span>'
                lim = ' <span class="bad">40턴 한도</span>' if r["result"] == "error_max_turns" else ""
                sk = ", ".join(r["skills"]) or "–"
                cells.append(f'<a class="cell c{c}" href="#r-{r["task"]}-{c}-{o}"><b>{r["k"]}. {esc(TNAME[r["task"]])}</b>'
                             f'<span>{r["p1"]}/{r["p2"]} · {chk}</span><span>{r["turns"]}턴{lim} · ${r["cost"]:.2f}</span>'
                             f'<span class="sm">시작 {r["context_start"] / 1000:.0f}k</span><span class="sm sk">{S(sk)}</span></a>')
            tot = sum(r["cost"] for r in rs)
            out.append(f'<div class="strip"><div class="sh"><b>{esc(CNAME[c])}</b> · {ONAME[o]} · 세션 합 ${tot:.2f}, {sum(r["turns"] for r in rs)}턴</div>'
                       f'<div class="cells">{"".join(cells)}</div></div>')
    pil = []
    for sess in sorted({r["session"] for r in D["pilot"]}):
        rs = sorted((r for r in D["pilot"] if r["session"] == sess), key=lambda r: r["k"])
        c, o = rs[0]["cond"], rs[0]["order"]
        cells = "".join(f'<div class="cell c{c}"><b>{r["k"]}. {esc(TNAME[r["task"]])}</b><span>{"통과" if r["check"] or (r["task"] == "docs" and c == "R") else "실패"}'
                        f'{"*" if (r["task"] == "docs" and c == "R") else ""}</span><span>{r["turns"]}턴{" · 40턴 한도" if r["result"] == "error_max_turns" else ""} · ${r["cost"]:.2f}</span>'
                        f'<span class="sm sk">{S(", ".join(r["skills"]) or "–")}</span></div>' for r in rs)
        pil.append(f'<div class="strip pilot"><div class="sh"><b>파일럿 {esc(CNAME[c])}</b> · {ONAME[o]} · 세션 합 ${sum(r["cost"] for r in rs):.2f} (점수 없음)</div><div class="cells">{cells}</div></div>')
    return "".join(out) + '<h3>파일럿 (본 집계 밖)</h3>' + "".join(pil) + \
        '<p class="sm">* 파일럿 R 정순 README는 처음 체크에서 경로 규칙(`data/orders.csv`) 때문에 실패했고, 본 실행 전 규칙 수정 뒤 다시 돌려 통과했다.</p>'


# ---------------------------------------------------------------- traces
def traces():
    a = [r for r in ROWS if r["trace_names"]]
    b = [r for r in ROWS if r["out_of_area"]]
    rows_a = "".join(f'<tr><td>{r["cond"]} {ONAME[r["order"]]}</td><td>{r["k"]}. {esc(TNAME[r["task"]])}</td><td>{S(", ".join(r["trace_names"]))}</td>'
                     f'<td>{"예(같은 요청이 다시 로드)" if not r["trace_names_not_reloaded"] else "아니오"}</td></tr>' for r in a) or '<tr><td colspan="4">없음</td></tr>'
    rows_b = "".join(f'<tr><td>{r["cond"]} {ONAME[r["order"]]}</td><td>{r["k"]}. {esc(TNAME[r["task"]])}</td><td>{esc(r["area"])}</td>'
                     f'<td>{S(", ".join(r["out_of_area"][:4]))}{f" 외 {len(r["out_of_area"]) - 4}개" if len(r["out_of_area"]) > 4 else ""}</td>'
                     f'<td>{S(", ".join(r["prior_skills"])) or "–"}</td></tr>' for r in sorted(b, key=lambda r: (r["cond"], r["order"], r["k"])))
    rows_c = "".join(f'<tr><td>{x["cond"]} {ONAME[x["order"]]}</td><td>{x["k"]}. {esc(TNAME[x["task"]])}</td><td>{S(", ".join(x["skills"]))}</td>'
                     f'<td>{sum(y["trace"] for y in x["results"])} / {len(x["results"])}</td></tr>'
                     for x in sorted(D["trace_c"], key=lambda x: (x["cond"], x["order"], x["k"])))
    return (f'<h3>(a) 앞 요청 스킬 이름이 답·diff에 나온 요청</h3><div class="tw"><table class="mt"><thead><tr><th>세션</th><th>요청</th><th>이름</th><th>그 요청도 로드</th></tr></thead><tbody>{rows_a}</tbody></table></div>'
            f'<h3>(b) 그 요청 영역 밖 파일을 바꾼 요청</h3><p class="sm">세 조건 모두 4요청씩이다. 대부분 앞서 쓴 문서(README, docs/)를 뒤 요청이 갱신한 것이다. P 역순 랜딩의 .taste-skill/ 파일은 그 요청이 부른 design-taste-frontend가 만든 점검 캡처·설정이다.</p>'
            f'<div class="tw"><table class="mt"><thead><tr><th>세션</th><th>요청</th><th>영역</th><th>영역 밖 파일</th><th>앞 요청까지 쓰인 스킬</th></tr></thead><tbody>{rows_b}</tbody></table></div>'
            f'<h3>(c) 판정자: 앞 스킬의 규칙이 이 결과물에 보이는가</h3><p class="sm">판정자는 결과물 diff와 앞 스킬의 이름·설명(본문 아님)만 보았다. "예"는 diff에서 그대로 옮긴 인용이 있어야 센다. 본 실행 15항목(스킬 쌍 62), 파일럿 5항목(32)에서 "예"는 0이다.</p>'
            f'<div class="tw"><table class="mt"><thead><tr><th>세션</th><th>요청</th><th>앞 요청까지 쓰인 스킬</th><th>예 / 스킬 수</th></tr></thead><tbody>{rows_c}</tbody></table></div>')


# ---------------------------------------------------------------- design slider (per order) and side-by-side
def slider(t, o, imgs, sid):
    out = []
    for sub, lab in (("screens", "데스크톱"), ("screens-375", "모바일 375")):
        got = {c: (run(t, c, o)["shots"].get(sub) or [None])[0] for c in CONDS}
        if not all(got[c] in imgs for c in CONDS):
            out.append(f'<div class="none">{lab}: 스크린샷 없음</div>')
            continue
        w = imgs[got["A"]][1][0]
        hmax = max(imgs[got[c]][1][1] for c in CONDS)
        ims = "".join(f'<img data-c="{c}" class="{"base" if c == "R" else "top" if c == "P" else "off"}" src="{imgs[got[c]][0]}" '
                      f'alt="{esc(t)} {c} {ONAME[o]} {lab}" width="{imgs[got[c]][1][0]}" height="{imgs[got[c]][1][1]}">' for c in CONDS)
        iid = f"{sid}-{'d' if sub == 'screens' else 'm'}"
        out.append(f'<figure class="ov {"mob" if sub != "screens" else ""}"><div class="pairs" role="group" aria-label="비교할 두 조건">'
                   + "".join(f'<button type="button" data-pair="{a}{b}" aria-pressed="{"true" if (a, b) == ("P", "R") else "false"}">{a} | {b}</button>' for a, b in g13.PAIRS)
                   + f'</div><div class="ovscroll"><div class="ovb" style="--pos:50%;aspect-ratio:{w}/{hmax}">{ims}<span class="tagl">P</span><span class="tagr">R</span></div></div>'
                   f'<label class="sr" for="{iid}">{lab} 경계</label><input id="{iid}" type="range" min="0" max="100" value="50">'
                   f'<figcaption>{lab} · 왼쪽 <b class="cl">P</b>, 오른쪽 <b class="cr">R</b> · 페이지 끝 아래는 빗금</figcaption></figure>')
    return '<div class="ovs">' + "".join(out) + "</div>"


def images():
    pngs = sorted({p for r in ROWS if r["task"] == "landing" for sub in ("screens", "screens-375") for p in r["shots"].get(sub, [])[:1]})
    enc = {p: v2.encode(p, 0.85, 66) for p in pngs}
    return {p: (f"data:image/webp;base64,{base64.b64encode(b).decode()}", sz) for p, (b, sz) in enc.items()}


def side_by_side(t, o, lc, rc, anchor):
    path = CORES[t]
    a, b = run(t, lc, o)["core_text"], run(t, rc, o)["core_text"]
    al, bl = a.split("\n"), b.split("\n")
    ah, bh = v2.highlight(a, path), v2.highlight(b, path)
    rows, texts, n = [], {}, 0

    def row(i, j, kind):
        nonlocal n
        n += 1
        rid = f"{anchor}-L{n}"
        texts[rid] = (al[i] if i is not None else "") + "\n" + (bl[j] if j is not None else "")
        lcell = f'<td class="ln">{i + 1}</td><td class="code {kind}">{ah[i]}</td>' if i is not None else '<td class="ln"></td><td class="code pad"></td>'
        rcell = f'<td class="ln">{j + 1}</td><td class="code {kind}">{bh[j]}</td>' if j is not None else '<td class="ln"></td><td class="code pad"></td>'
        rows.append(f'<tr id="{rid}">{lcell}{rcell}</tr>')
    ops = difflib.SequenceMatcher(None, al, bl, autojunk=False).get_opcodes()
    for oi, (op, i1, i2, j1, j2) in enumerate(ops):
        if op == "equal":
            kh, kt = (0 if oi == 0 else 3), (0 if oi == len(ops) - 1 else 3)
            span = i2 - i1
            if span <= kh + kt + 2:
                for k in range(span):
                    row(i1 + k, j1 + k, "eq")
                continue
            for k in range(kh):
                row(i1 + k, j1 + k, "eq")
            rows.append(f'<tr class="fold"><td colspan="4">… 같은 줄 {span - kh - kt}개 …</td></tr>')
            for k in range(span - kt, span):
                row(i1 + k, j1 + k, "eq")
        else:
            for k in range(max(i2 - i1, j2 - j1)):
                i = i1 + k if k < i2 - i1 else None
                j = j1 + k if k < j2 - j1 else None
                row(i, j, "chg" if i is not None and j is not None else ("del" if i is not None else "add"))
    head = f'<div class="sbs-h"><span>{lc} {ONAME[o]} · {len(al)}줄</span><span>{rc} {ONAME[o]} · {len(bl)}줄</span></div>'
    body = ('<p class="sm">두 결과의 이 파일이 같다.</p>' if a == b else
            f'<div class="tw sbs-w"><table class="sbs"><colgroup><col class="lnc"><col><col class="lnc"><col></colgroup>{"".join(rows)}</table></div>')
    return head + body, texts


def table(t):
    land = t == "landing"
    head = ("<tr><th>결과</th><th>위치</th><th>p1 / p2</th>" + ("<th>AI느낌 p1 / p2</th>" if land else "") +
            "<th>체크</th><th>파일</th><th>+ / −</th><th>추가 테스트</th><th>턴</th><th>API 환산</th><th>시작 컨텍스트</th><th>스킬(그 요청)</th><th>영역 밖 파일</th></tr>")
    rows = []
    for c in CONDS:
        for o in ORDERS:
            r = run(t, c, o)
            a = r["auto"]
            chk = '<span class="ok">통과</span>' if r["check"] else '<span class="bad">실패</span>'
            lim = ' <span class="bad">한도</span>' if r["result"] == "error_max_turns" else ""
            mk = f' · 변이 {r["mutants_killed"]}/8' if r.get("mutants_killed") is not None else ""
            ai = f'<td class="num">{r["ai_look"][0]} / {r["ai_look"][1]}</td>' if land else ""
            rows.append(f'<tr id="r-{t}-{c}-{o}" class="c{c}"><th>{c} {ONAME[o]}</th><td class="num">{r["k"]}번째</td><td class="num">{r["p1"]} / {r["p2"]}</td>{ai}'
                        f'<td>{chk}{mk}</td><td class="num">{a["files"]}</td><td class="num">+{a["added"]} −{a["deleted"]}</td><td class="num">{a["tests_added"]}</td>'
                        f'<td class="num">{r["turns"]}{lim}</td><td class="num">${r["cost"]:.2f}</td><td class="num">{r["context_start"] / 1000:.0f}k</td>'
                        f'<td>{S(", ".join(r["skills"])) or "–"}</td><td>{len(r["out_of_area"]) or "–"}</td></tr>')
    return f'<div class="tw"><table class="mt"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def summary_block(t, row_texts):
    d = DIFFS[t]
    lines = []
    for li in d["lines"]:
        qs = []
        for q in li["quotes"]:
            r = run_of(t, q["run"])
            target = f'#r-{t}-{r["cond"]}-{r["order"]}'
            if q["src"] == "diff":
                for (tt, o, pair), texts in row_texts.items():
                    if tt == t and o == r["order"] and r["cond"] in pair:
                        side = pair.index(r["cond"])
                        hit = next((rid for rid, txt in texts.items() if q["quote"].strip() in txt.split("\n")[side]), None)
                        if hit:
                            target = f"#{hit}"
                            break
            c, o = q["run"].split()
            qs.append(f'<li><a class="src" href="{target}">{esc(q["src"])} · {c} {ONAME[o]}</a> <q>{S(q["quote"])}</q></li>')
        lines.append(f'<li><p>{S(li["text"])}</p><ul class="qs">{"".join(qs)}</ul></li>')
    return (f'<div class="sb" id="sum-{t}"><div class="sbh"><h4><a href="#t-{t}">{esc(TNAME[t])}</a></h4>'
            f'<span class="pill {"same" if d["verdict"] == "차이 없음" else "diff"}">{esc(d["verdict"])}</span></div><ol class="dl">{"".join(lines)}</ol></div>')


def reasons_block(t):
    items = []
    for c in CONDS:
        for o in ORDERS:
            r = run(t, c, o)
            ps = "".join(f'<p class="why"><b>{p}</b> {S(r["reason_" + p])}</p>' for p in ("p1", "p2"))
            items.append(f'<div class="rr c{c}"><h5>{c} {ONAME[o]} · {r["k"]}번째 요청</h5>{ps}</div>')
    return f'<details class="rsn"><summary>결과별 판정 근거</summary><div class="rrs">{"".join(items)}</div></details>'


def main():
    bad = verify_quotes()
    if bad:
        print(json.dumps({"unverified_quotes": bad}, ensure_ascii=False, indent=1))
        raise SystemExit("summaries not ready")
    imgs = images()
    reqs = (E2E / "stage14" / "requests.md").read_text()
    sections, row_texts = [], {}
    for t in TASKS:
        prompt = re.search(rf"^## \d {t} \(\w+\)\n((?:> .*\n?)+)", reqs, re.M).group(1)
        prompt = "\n".join(l[2:] for l in prompt.strip().splitlines())
        parts = [f'<div class="task" id="t-{t}"><h3>{esc(TNAME[t])} <span class="sm">{esc(t)}</span> <a class="up" href="#sum-{t}">차이 정리로</a></h3>',
                 f'<details class="prompt"><summary>요청 원문</summary><p>{S(prompt)}</p></details>', table(t)]
        if t == "landing":
            for k, o in enumerate(ORDERS):
                pos = "첫" if o == "F" else "마지막"
                parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>{ONAME[o]}({pos} 요청): A · P · R 화면</summary>{slider(t, o, imgs, f"s-{t}-{o}")}</details>')
        elif CORES.get(t):
            parts.append(f'<p class="cf">핵심 파일 <code>{S(CORES[t])}</code> · 그 요청이 끝난 시점의 파일(세션 diff를 차례로 적용해 다시 만듦)</p>')
            for k, o in enumerate(ORDERS):
                views = []
                for lc, rc in g13.CODE_PAIRS:
                    h, texts = side_by_side(t, o, lc, rc, f"d-{t}-{o}-{lc}{rc}")
                    row_texts[(t, o, lc + rc)] = texts
                    views.append(f'<div class="sbsv"><p class="pl">{lc} | {rc}</p>{h}</div>')
                parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>{ONAME[o]}: A | P, P | R</summary>{"".join(views)}</details>')
        parts.append(reasons_block(t))
        parts.append("</div>")
        sections.append("".join(parts))
    summ = '<div class="sgrid">' + "".join(summary_block(t, row_texts) for t in TASKS) + "</div>"
    cr, cost, eff, Dv = SUM["criteria"], SUM["cost_session_mean"], SUM["efficiency"], SUM["D"]
    lab = lambda x: "판정 노이즈 안" if x["noise"] else "노이즈 밖"  # noqa: E731
    crit = (f'<tr><th>(i) 6작업 평균 R − P</th><td class="num">{cr["i_R_minus_P"]["a"]:.3f} − {cr["i_R_minus_P"]["b"]:.3f}</td><td class="num"><b>{cr["i_R_minus_P"]["diff"]:+.3f}</b></td><td>{lab(cr["i_R_minus_P"])}</td></tr>'
            f'<tr><th>(ii) 6작업 평균 R − A</th><td class="num">{cr["ii_R_minus_A"]["a"]:.3f} − {cr["ii_R_minus_A"]["b"]:.3f}</td><td class="num"><b>{cr["ii_R_minus_A"]["diff"]:+.3f}</b></td><td>{lab(cr["ii_R_minus_A"])}</td></tr>'
            f'<tr><th>(iii) 영역 바뀐 직후 R − P</th><td class="num">{cr["iii_R_minus_P_after_domain_change"]["a"]:.3f} − {cr["iii_R_minus_P_after_domain_change"]["b"]:.3f}</td><td class="num"><b>{cr["iii_R_minus_P_after_domain_change"]["diff"]:+.3f}</b></td><td>{lab(cr["iii_R_minus_P_after_domain_change"])}</td></tr>'
            f'<tr><th>(iv) 세션 평균 API 단가 환산</th><td class="num">R ${cost["R"]:.2f} · P ${cost["P"]:.2f} · A ${cost["A"]:.2f}</td><td class="num">R−P {eff["R_vs_P"]["score_per_dollar"]}점/$ · R−A {eff["R_vs_A"]["score_per_dollar"]}점/$</td><td>–</td></tr>')
    head = f"""<header class="wrap"><p class="eyebrow">skillfetch e2e · Stage 14</p><h1>연속 작업 갤러리</h1>
<p>한 세션(<code>--resume</code>)에서 종류가 다른 작업 6개를 연달아 보냈다. 랜딩 → API → API 테스트 → Rust 동시성 → README → 데이터 스크립트(정순), 그리고 데이터 → README → Rust → API → API 테스트 → 랜딩(역순)이다.
레포는 영역 네 개(<code>web/</code>, <code>api/</code>, <code>media/</code>, <code>data/</code>)가 있는 모노레포 하나다. <b>A</b>는 스킬 없음, <b>P</b>는 Stage 13의 인기 스킬 8개를 고정 설치, <b>R</b>은 배포본 라우터와 출시 index다. 조건 × 순서 2 × 1회로, 세션 6개, 요청 36개다.</p>
<p>점수는 작업마다 결과물 6개를 한 세트로 섞은 1–5 블라인드 판정(Claude p1, p2)이다. "차이 정리"의 인용은 빌드 때 판정 근거·diff 원문과 대조했다. API 단가 환산 합계는 본 실행 $87.13 + 파일럿 $43.02 = $130.15다(상한 $140). 보고서는 <code>stage14/report-14.md</code>다.</p>
<div class="tw"><table class="mt tot"><thead><tr><th>기준(실행 전 고정)</th><th>R − 비교</th><th>차</th><th>D = {Dv}</th></tr></thead><tbody>{crit}</tbody></table></div>
<p class="sm">D = max(조건별 |p1 − p2| 평균의 최댓값, 0.25). "판정 노이즈 안"은 표시이고 게이트가 아니다. 반복이 1회라 조건마다 세션 2개다. (i)·(iii)에는 P 랜딩 두 결과(1.0, 2.0)가 크게 들어간다. 랜딩을 뺀 참고 줄은 R − P +0.40, R − A 0.00이다.</p></header>"""
    nav = ('<nav class="wrap"><a href="#sessions">세션 흐름</a><a href="#charts">차트</a><a href="#summary">차이 정리</a><a href="#traces">흔적</a>'
           + "".join(f'<a href="#t-{t}">{esc(TNAME[t])}</a>' for t in TASKS) + "</nav>")
    doc = (f'<title>Stage 14 연속 작업 갤러리</title><link rel="preconnect" href="https://fonts.googleapis.com">'
           f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">'
           f'<style>{g.CSS}{v2.CSS}{g13.CSS}{CSS}</style>{head}{nav}<main class="wrap">'
           f'<section id="sessions"><h2>세션 흐름</h2>{strips()}</section>'
           f'<section id="charts"><h2>A / P / R</h2>{charts()}</section>'
           f'<section id="summary"><h2>차이 정리</h2>{summ}</section>'
           f'<section id="traces"><h2>앞 요청 스킬의 흔적</h2>{traces()}</section>'
           f'<section>{"".join(sections)}</section></main><script>{g13.JS}</script>')
    for pat in (r"/Users/", r"\b" + re.escape(Path.home().name) + r"\b", r"skillfetch-e2e-wt", r"/private/tmp", re.escape(str(E2E.parent))):
        assert not re.search(pat, doc), f"publication rule: {pat} present"
    OUT.write_text(doc)
    size = OUT.stat().st_size
    print(json.dumps({"bytes": size, "MB": round(size / 1024 / 1024, 2), "rows": len(ROWS), "summaries": len(DIFFS)}))
    assert size < 16 * 1024 * 1024


CSS = """
.strip{margin:10px 0}.strip .sh{font-size:13px;margin-bottom:4px}.cells{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}
.cell{display:flex;flex-direction:column;gap:2px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px 8px;font-size:12px;color:var(--fg);text-decoration:none;min-width:0}
.cell.cA{border-top:3px solid var(--b-A)}.cell.cP{border-top:3px solid var(--b-P)}.cell.cR{border-top:3px solid var(--b-R)}
.cell .sk{overflow-wrap:anywhere}#traces .mt td:nth-child(-n+2){white-space:nowrap}.strip.pilot .cell{opacity:.85}
@media (max-width:760px){.cells{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""

if __name__ == "__main__":
    main()
