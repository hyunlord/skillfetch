#!/usr/bin/env python3
"""Build stage13/gallery/stage13-gallery.html (gallery v2 format, three conditions) from stage13-private/gallery-data-13.json
(assemble_13.py) and the difference summaries stage13-private/gallery-diffs/<task>.json. No new sessions. Every summary
quote is checked against its source (the run's Stage 13 judge reason or its diff) and the build stops if one does not match
(rule kept from gallery v1/v2).
Page:
  top      d1-landing P | R: the three repetitions' full desktop pages side by side (P ended at the 40-turn limit with blank
           sections; R), with the judges' reasons; then five bar charts, one row per task, A / P / R: Claude score (mean of
           (p1+p2)/2), check pass rate, test functions added (mean per run), turns (median), API-price equivalent (mean);
           then "차이 정리" per task, each quote linked to the diff row or the run's row in the metrics table
  task     metrics table of every run; design: overlay slider per repetition with a pair switch (P|R, A|P, A|R; desktop and
           mobile); code: the task's core file (most-changed non-test, non-lock, non-README file over all nine runs) side by
           side, A|P and P|R per repetition (A|R is in the Stage Q gallery v2), syntax-highlighted, unchanged lines folded;
           judge reasons per run, folded
Publication rules as v1/v2 (no user paths or names; skills by name only). usage: build_gallery_13.py"""
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
import build_gallery_s10 as g  # noqa: E402
import build_gallery_v2 as v2  # noqa: E402
from autometrics import apply_chunk, split  # noqa: E402

OUT = E2E / "stage13" / "gallery" / "stage13-gallery.html"
D = json.loads((E2E / "stage13-private" / "gallery-data-13.json").read_text())
TASKS, RUNS = D["tasks"], D["runs"]
DIFFS = {p.stem: json.loads(p.read_text()) for p in (E2E / "stage13-private" / "gallery-diffs").glob("*.json")}
STACK_ORDER = ["디자인", "Rust", "Swift", "Go", "Java", "TypeScript", "Python"]
ORDER = sorted(TASKS, key=lambda t: (t != "d1-landing", STACK_ORDER.index(TASKS[t]["stack"]), TASKS[t]["source"], t))
CONDS = ("A", "P", "R")
CNAME = {"A": "A 스킬 없음", "P": "P 인기 스킬 8개", "R": "R 라우터"}
PAIRS = (("P", "R"), ("A", "P"), ("A", "R"))
CODE_PAIRS = (("A", "P"), ("P", "R"))
esc, S = v2.esc, g.S
BUDGET = 15.0 * 1024 * 1024


def runs_of(t, c=None):
    return sorted((r for r in RUNS if r["task"] == t and (c is None or r["cond"] == c)), key=lambda r: (CONDS.index(r["cond"]), r["tag"]))


def run(t, c, tag):
    return next((r for r in RUNS if r["task"] == t and r["cond"] == c and r["tag"] == tag), None)


def claude(r):
    s = r["scores"]
    return (s["p1"]["score"] + s["p2"]["score"]) / 2


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def run_of(t, label):
    m = re.match(r"([APR])\s+(m\d)$", label.strip())
    return run(t, m.group(1), m.group(2)) if m else None


def verify_quotes():
    bad = []
    for t, d in DIFFS.items():
        for li in d["lines"]:
            for q in li["quotes"]:
                r = run_of(t, q["run"])
                src = "" if not r else (g.diff_text(r) if q["src"] == "diff" else r["reasons"].get(q["src"], {}).get("reason", ""))
                if not q["quote"] or q["quote"] not in src:
                    bad.append(f"{t} | {q['src']} {q['run']} | {q['quote'][:80]}")
    return bad


# ---------------------------------------------------------------- charts
def chart(title, unit, vals, vmax, fmtv, ticks=None):
    row, lab, w, pad, bh = 32, 104, 360, 34, 7
    h = len(ORDER) * row + 34
    bw = w - lab - pad
    if ticks is None:
        step = {5: 1, 10: 2, 15: 3, 20: 5, 25: 5, 30: 5, 40: 10, 50: 10, 60: 10, 80: 20, 100: 25}.get(vmax, vmax / 4)
        ticks = [step * i for i in range(int(round(vmax / step)) + 1)]
    out = [f'<figure class="chart"><figcaption>{esc(title)} <span class="sm">{esc(unit)}</span></figcaption>'
           f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">']
    for tv in ticks:
        x = lab + bw * tv / vmax
        out.append(f'<line x1="{x:.1f}" y1="6" x2="{x:.1f}" y2="{h - 22}" class="grid"/>'
                   f'<text x="{x:.1f}" y="{h - 8}" class="tick" text-anchor="middle">{fmtv(tv)}</text>')
    for i, t in enumerate(ORDER):
        y = 8 + i * row
        out.append(f'<text x="{lab - 6}" y="{y + 15}" class="lab" text-anchor="end">{esc(t)}</text>')
        for j, c in enumerate(CONDS):
            v = vals[t][c]
            yy = y + j * (bh + 1.5)
            ww = max(0.0, min(bw, bw * v / vmax)) if v is not None else 0
            out.append(f'<rect x="{lab}" y="{yy:.1f}" width="{ww:.1f}" height="{bh}" class="b-{c}"><title>{esc(t)} {c} {fmtv(v)}</title></rect>'
                       f'<text x="{lab + ww + 3:.1f}" y="{yy + 6.5:.1f}" class="val">{fmtv(v)}</text>')
    out.append("</svg></figure>")
    return "".join(out)


def charts():
    def per(fn):
        return {t: {c: fn(runs_of(t, c)) for c in CONDS} for t in ORDER}
    score = per(lambda rs: mean([claude(r) for r in rs]))
    check = per(lambda rs: 100 * sum(r["check_pass"] is True for r in rs) / len(rs))
    tests = per(lambda rs: mean([r["auto"]["tests_added"] for r in rs]))
    turns = per(lambda rs: st.median([r["turns"] for r in rs if r["turns"] is not None]))
    cost = per(lambda rs: mean([r["cost_usd"] for r in rs]))
    nice = lambda v: next(n for n in (5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100) if n >= v)  # noqa: E731
    tmax = nice(max([v for x in tests.values() for v in x.values() if v is not None] + [1]))
    nmax = nice(max([v for x in turns.values() for v in x.values() if v is not None] + [1]))
    cmax = max(v for x in cost.values() for v in x.values())
    cmax = 1.0 if cmax <= 1 else float(int(cmax) + 1)
    num = lambda v: "–" if v is None else (f"{v:.1f}" if v % 1 else f"{v:.0f}")  # noqa: E731
    legend = ('<p class="legend">' + "".join(f'<span class="sw {c}"></span>{esc(CNAME[c])} ' for c in CONDS) + "</p>")
    return legend + '<div class="charts">' + "".join([
        chart("점수", "Claude (p1+p2)/2 평균, 1–5", score, 5, num),
        chart("체크 통과", "%", check, 100, lambda v: f"{v:.0f}"),
        chart("추가한 테스트 함수", "실행당 평균", tests, tmax, num),
        chart("턴", "중앙값", turns, nmax, num),
        chart("API 단가 환산", "세션 평균, 달러", cost, cmax, lambda v: f"{v:.2f}",
              ticks=[cmax * i / 4 for i in range(5)])]) + "</div>"


# ---------------------------------------------------------------- code: side-by-side view of two conditions
def core_file(t):
    tot = {}
    for r in runs_of(t):
        for f, ch in split(g.diff_text(r)).items():
            if v2.SKIP.search(f) or f.startswith("."):
                continue
            tot[f] = tot.get(f, 0) + sum(1 for l in ch.split("\n") if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    return max(tot, key=tot.get) if tot else None


def base_text(t, path):
    import subprocess
    p = subprocess.run(["git", "-C", str(E2E / "repos" / TASKS[t]["repo"]), "show", f"{TASKS[t]['base_branch']}:{path}"],
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ""


def final_text(r, path, base):
    ch = split(g.diff_text(r)).get(path)
    if ch is None:
        return base
    return apply_chunk(base, ch) or ""


def side_by_side(t, tag, path, lc, rc, anchor):
    left, right = run(t, lc, tag), run(t, rc, tag)
    base = base_text(t, path)
    a, b = final_text(left, path, base), final_text(right, path, base)
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
            keep_head = 0 if oi == 0 else 3
            keep_tail = 0 if oi == len(ops) - 1 else 3
            span = i2 - i1
            if span <= keep_head + keep_tail + 2:
                for k in range(span):
                    row(i1 + k, j1 + k, "eq")
                continue
            for k in range(keep_head):
                row(i1 + k, j1 + k, "eq")
            rows.append(f'<tr class="fold"><td colspan="4">… 같은 줄 {span - keep_head - keep_tail}개 …</td></tr>')
            for k in range(span - keep_tail, span):
                row(i1 + k, j1 + k, "eq")
        else:
            for k in range(max(i2 - i1, j2 - j1)):
                i = i1 + k if k < i2 - i1 else None
                j = j1 + k if k < j2 - j1 else None
                row(i, j, "chg" if i is not None and j is not None else ("del" if i is not None else "add"))
    head = f'<div class="sbs-h"><span>{lc} {esc(tag)} · {len(al)}줄</span><span>{rc} {esc(tag)} · {len(bl)}줄</span></div>'
    body = ('<p class="sm">두 결과의 이 파일이 같다.</p>' if a == b else
            f'<div class="tw sbs-w"><table class="sbs"><colgroup><col class="lnc"><col><col class="lnc"><col></colgroup>'
            f'{"".join(rows)}</table></div>')
    return head + body, texts


# ---------------------------------------------------------------- design: images, pair slider, d1-landing P | R
def images():
    pngs = sorted({p for r in RUNS if r["bundle"] == 1 for sub in ("screens", "screens-375") for p in r["shots"].get(sub, [])[:1]})
    for scale, q in ((0.85, 66), (0.7, 60), (0.55, 54), (0.45, 50)):
        enc = {p: v2.encode(p, scale, q) for p in pngs}
        total = sum(len(b) * 4 / 3 for b, _ in enc.values())
        if total < BUDGET - 5 * 1024 * 1024:
            return {p: (f"data:image/webp;base64,{base64.b64encode(b).decode()}", sz) for p, (b, sz) in enc.items()}, scale, q
    raise SystemExit("images do not fit the budget")


def shot(r, sub):
    xs = (r or {}).get("shots", {}).get(sub, [])
    return xs[0] if xs else None


def slider(t, tag, imgs, sid):
    out = []
    for sub, lab in (("screens", "데스크톱"), ("screens-375", "모바일 375")):
        got = {c: shot(run(t, c, tag), sub) for c in CONDS}
        if not all(got[c] in imgs for c in CONDS):
            out.append(f'<div class="none">{lab}: 스크린샷 없음 ({", ".join(c for c in CONDS if got[c] not in imgs)})</div>')
            continue
        w = imgs[got["A"]][1][0]
        hmax = max(imgs[got[c]][1][1] for c in CONDS)
        ims = "".join(
            f'<img data-c="{c}" class="{"base" if c == "R" else "top" if c == "P" else "off"}" src="{imgs[got[c]][0]}" '
            f'alt="{esc(t)} {c} {esc(tag)} {lab}" width="{imgs[got[c]][1][0]}" height="{imgs[got[c]][1][1]}">' for c in CONDS)
        iid = f"{sid}-{'d' if sub == 'screens' else 'm'}"
        out.append(f'<figure class="ov {"mob" if sub != "screens" else ""}" data-l="P" data-r="R">'
                   f'<div class="pairs" role="group" aria-label="비교할 두 조건">'
                   + "".join(f'<button type="button" data-pair="{a}{b}" aria-pressed="{"true" if (a, b) == ("P", "R") else "false"}">{a} | {b}</button>' for a, b in PAIRS)
                   + f'</div><div class="ovscroll"><div class="ovb" style="--pos:50%;aspect-ratio:{w}/{hmax}">{ims}'
                   f'<span class="tagl">P</span><span class="tagr">R</span></div></div>'
                   f'<label class="sr" for="{iid}">{lab} 경계</label><input id="{iid}" type="range" min="0" max="100" value="50">'
                   f'<figcaption>{lab} · 왼쪽 <b class="cl">P</b>, 오른쪽 <b class="cr">R</b> · 페이지 끝 아래는 회색</figcaption></figure>')
    return '<div class="ovs">' + "".join(out) + "</div>"


def spotlight():
    t = "d1-landing"
    cols = []
    for tag in ("m1", "m2", "m3"):
        cells = []
        for c in ("P", "R"):
            r = run(t, c, tag)
            p = shot(r, "screens")
            b, (w, h) = v2.encode(p, 0.34, 58)
            sc = r["scores"]
            why = r["reasons"]["p1"]["reason"]
            end = "40턴 한도에서 끝남" if r["result"] == "error_max_turns" else f"{r['turns']}턴"
            sk = ", ".join(r["loaded"]) or "–"
            cells.append(f'<figure class="spc {c}"><figcaption><b>{c} {tag}</b> · 쓸만함 p1 {sc["p1"]["score"]} / p2 {sc["p2"]["score"]}'
                         f' · {end} · API 단가 환산 ${r["cost_usd"]:.2f}<br><span class="sm">{"P 스킬" if c == "P" else "로드"}: {S(sk)}</span></figcaption>'
                         f'<div class="spi"><img src="data:image/webp;base64,{base64.b64encode(b).decode()}" alt="d1-landing {c} {tag} 데스크톱 전체" '
                         f'width="{w}" height="{h}" loading="lazy"></div><p class="why"><b>p1</b> {S(why)}</p></figure>')
        cols.append(f'<div class="spr"><h4>{tag}</h4><div class="spg">{"".join(cells)}</div></div>')
    return ('<section id="d1"><h2>d1-landing: P와 R</h2>'
            '<p class="sm">세 반복의 데스크톱 전체 페이지(1280 폭 캡처를 줄임)를 나란히 놓았다. P는 섹션을 opacity 0으로 숨겼다가 IntersectionObserver로 '
            '보이게 하는 방식이라, 정지 화면 캡처에서 기능·가격 자리가 빈칸이다. 아래 "차이 정리"의 d1-landing 항목에 근거 인용이 있다.</p>'
            f'<div class="sps">{"".join(cols)}</div></section>')


# ---------------------------------------------------------------- tables and summaries
def metrics_table(t):
    design = TASKS[t]["bundle"] == 1
    head = ("<tr><th>실행</th><th>p1 / p2</th>" + ("<th>AI느낌 p1 / p2</th>" if design else "") +
            "<th>체크</th><th>추가 테스트</th><th>README</th><th>의존성</th><th>파일</th><th>+ / −</th><th>턴</th><th>API 환산</th>"
            "<th>P 스킬 / R 로드</th><th>Skill 호출</th></tr>")
    rows = []
    for r in runs_of(t):
        s, a = r["scores"], r["auto"]
        chk = '<span class="ok">통과</span>' if r["check_pass"] else ('<span class="bad">실패</span>' if r["check_pass"] is False else "–")
        turns = g.fmt(r["turns"]) + (' <span class="bad">한도</span>' if r["result"] == "error_max_turns" else "")
        ai = (f'<td class="num">{s["p1"]["ai_look"]} / {s["p2"]["ai_look"]}</td>' if design else "")
        rows.append(f'<tr id="r-{t}-{r["cond"]}-{r["tag"]}" class="c{r["cond"]}"><th>{r["cond"]} {esc(r["tag"])}</th>'
                    f'<td class="num">{s["p1"]["score"]} / {s["p2"]["score"]}</td>{ai}<td>{chk}</td>'
                    f'<td class="num">{a["tests_added"]}</td><td>{"바꿈" if a["readme"] else "–"}</td>'
                    f'<td>{S(", ".join(a["deps"])) or "–"}</td><td class="num">{a["files"]}</td><td class="num">+{a["added"]} −{a["deleted"]}</td>'
                    f'<td class="num">{turns}</td><td class="num">${r["cost_usd"]:.2f}</td>'
                    f'<td>{S(", ".join(r["loaded"])) or "–"}</td><td>{S(", ".join(r["skill_calls"])) or "–"}</td></tr>')
    return f'<div class="tw"><table class="mt"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


def src_label(t):
    return "Stage Q 태스크" if TASKS[t]["source"] == "Q" else "Q1 확장 태스크"


def summary_block(t, row_texts):
    d = DIFFS.get(t)
    if not d:
        return f'<div class="sb" id="sum-{t}"><div class="sbh"><h4><a href="#t-{t}">{esc(t)}</a></h4></div><p class="sm">차이 정리 없음</p></div>'
    lines = []
    for li in d["lines"]:
        qs = []
        for q in li["quotes"]:
            r = run_of(t, q["run"])
            target = f'#r-{t}-{r["cond"]}-{r["tag"]}'
            if q["src"] == "diff":
                body = q["quote"].strip()
                for (tt, tag, pair), texts in row_texts.items():
                    if tt == t and tag == r["tag"] and r["cond"] in pair:
                        side = pair.index(r["cond"])
                        hit = next((rid for rid, txt in texts.items() if body and body in txt.split("\n")[side]), None)
                        if hit:
                            target = f"#{hit}"
                            break
            qs.append(f'<li><a class="src" href="{target}">{esc(q["src"])} · {esc(q["run"])}</a> <q>{S(q["quote"])}</q></li>')
        lines.append(f'<li><p>{S(li["text"])}</p><ul class="qs">{"".join(qs)}</ul></li>')
    return (f'<div class="sb" id="sum-{t}"><div class="sbh"><h4><a href="#t-{t}">{esc(t)}</a></h4>'
            f'<span class="pill {"same" if d["verdict"] == "차이 없음" else "diff"}">{esc(d["verdict"])}</span>'
            f'<span class="sm">{esc(TASKS[t]["stack"])} · {src_label(t)}</span></div><ol class="dl">{"".join(lines)}</ol></div>')


def reasons_block(t):
    items = []
    for r in runs_of(t):
        rs = r["reasons"]
        ps = "".join(f'<p class="why"><b>{p}</b> {S(rs[p]["reason"])}</p>' for p in ("p1", "p2") if p in rs)
        items.append(f'<div class="rr c{r["cond"]}"><h5>{r["cond"]} {esc(r["tag"])}</h5>{ps}</div>')
    return f'<details class="rsn"><summary>실행별 판정 근거</summary><div class="rrs">{"".join(items)}</div></details>'


def main():
    bad = verify_quotes()
    if bad:
        print(json.dumps({"unverified_quotes": bad}, ensure_ascii=False, indent=1))
        raise SystemExit("summaries not ready")
    imgs, scale, q = images()
    sections, row_texts = [], {}
    for t in ORDER:
        parts = [f'<div class="task" id="t-{t}"><h3>{esc(t)} <span class="sm">{esc(TASKS[t]["stack"])} · {src_label(t)}</span> '
                 f'<a class="up" href="#sum-{t}">차이 정리로</a></h3>',
                 f'<details class="prompt"><summary>요청 원문</summary><p>{S(TASKS[t]["prompt"])}</p></details>', metrics_table(t)]
        if TASKS[t]["bundle"] == 1:
            for k, tag in enumerate(("m1", "m2", "m3")):
                parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>{tag}: A · P · R 화면</summary>'
                             f'{slider(t, tag, imgs, f"s-{t}-{tag}")}</details>')
        else:
            cf = core_file(t)
            if cf:
                parts.append(f'<p class="cf">핵심 파일 <code>{S(cf)}</code> · A|R 나란히 보기는 Stage Q 갤러리 v2에 있다.</p>')
                for k, tag in enumerate(("m1", "m2", "m3")):
                    views = []
                    for lc, rc in CODE_PAIRS:
                        h, texts = side_by_side(t, tag, cf, lc, rc, f"d-{t}-{tag}-{lc}{rc}")
                        row_texts[(t, tag, lc + rc)] = texts
                        views.append(f'<div class="sbsv"><p class="pl">{lc} | {rc}</p>{h}</div>')
                    parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>{tag}: A | P, P | R</summary>{"".join(views)}</details>')
        parts.append(reasons_block(t))
        parts.append("</div>")
        sections.append("".join(parts))
    summ = '<div class="sgrid">' + "".join(summary_block(t, row_texts) for t in ORDER) + "</div>"
    n = {c: sum(r["cond"] == c for r in RUNS) for c in CONDS}
    avg = {c: mean([claude(r) for r in RUNS if r["cond"] == c]) for c in CONDS}
    chk = {c: sum(r["check_pass"] is True for r in RUNS if r["cond"] == c) for c in CONDS}
    cst = {c: mean([r["cost_usd"] for r in RUNS if r["cond"] == c]) for c in CONDS}
    tot = "".join(f'<tr><th>{esc(CNAME[c])}</th><td class="num">{n[c]}</td><td class="num">{avg[c]:.3f}</td><td class="num">{chk[c]}/{n[c]}</td>'
                  f'<td class="num">${cst[c]:.3f}</td></tr>' for c in CONDS)
    head = f"""<header class="wrap"><p class="eyebrow">skillfetch e2e · Stage 13</p><h1>A · P · R 갤러리</h1>
<p><b>A</b> 스킬·라우터 없음. <b>P</b> 인기 공개 스킬 8개를 레포 <code>.claude/skills</code>에 설치하고 라우터는 없음
(improve-codebase-architecture, tdd, frontend-design, domain-modeling, vercel-react-best-practices, web-design-guidelines,
design-taste-frontend, vercel-composition-patterns). <b>R</b> 라우터 S-b′ + skillfetch MCP. 환경은 E1이다.
태스크 18개 × 조건 3개 × 3회로, 실행은 {len(RUNS)}개다. A·R은 Stage Q와 Q1 확장의 실행을 다시 썼다(Stage Q 태스크 6개의 3회차는 Stage 13에서 새로 돌렸다). P는 새로 돌렸다.</p>
<p>점수는 Stage 13에서 A·P·R 아홉 개를 한 세트로 섞어 새로 받은 1–5 블라인드 판정(Claude p1, p2)이다. 추가 테스트, README, 의존성, 파일·줄 수는 diff에서 자동으로 셌다.
"차이 정리"의 각 줄에는 판정 근거나 diff에서 그대로 옮긴 인용을 붙였다. 빌드 때 원문과 대조했고, 인용을 누르면 해당 diff 줄이나 실행 행으로 간다.</p>
<div class="tw"><table class="mt tot"><thead><tr><th>조건</th><th>실행</th><th>점수 평균</th><th>체크 통과</th><th>API 단가 환산 평균</th></tr></thead><tbody>{tot}</tbody></table></div>
<p class="sm">디자인은 슬라이더로 두 조건의 화면을 겹쳐 보고 위 버튼으로 짝(P|R, A|P, A|R)을 바꾼다. 코드 태스크는 핵심 파일 하나를 A|P, P|R로 나란히 보인다(시작 커밋에 각 실행의 변경을 적용해 다시 만듦, 같은 줄은 접음).
스크린샷은 크기 {int(scale * 100)}%, WebP {q}로 다시 인코딩했다. 보고서는 <code>stage13/report-13.md</code>다.</p></header>"""
    nav = '<nav class="wrap"><a href="#d1">d1-landing P·R</a><a href="#charts">차트</a><a href="#summary">차이 정리</a>' + "".join(
        f'<a href="#t-{t}">{esc(t)}</a>' for t in ORDER) + "</nav>"
    doc = (f'<title>Stage 13 A·P·R 갤러리</title><link rel="preconnect" href="https://fonts.googleapis.com">'
           f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">'
           f'<style>{g.CSS}{v2.CSS}{CSS}</style>{head}{nav}<main class="wrap">{spotlight()}'
           f'<section id="charts"><h2>태스크별 A / P / R</h2>{charts()}</section>'
           f'<section id="summary"><h2>차이 정리</h2>{summ}</section><section>{"".join(sections)}</section></main><script>{JS}</script>')
    for pat in (r"/Users/", r"\b" + re.escape(Path.home().name) + r"\b", r"skillfetch-e2e-wt", r"/private/tmp", re.escape(str(E2E.parent))):
        assert not re.search(pat, doc), f"publication rule: {pat} present"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc)
    size = OUT.stat().st_size
    print(json.dumps({"bytes": size, "MB": round(size / 1024 / 1024, 2), "runs": len(RUNS), "tasks": len(ORDER), "image_scale": scale,
                      "webp_q": q, "summaries": len(DIFFS), "missing_summaries": [t for t in ORDER if t not in DIFFS],
                      "means": {c: round(avg[c], 3) for c in CONDS}, "checks": chk}, ensure_ascii=False))
    assert size < 16 * 1024 * 1024


CSS = """
:root{--b-A:#a7a397;--b-P:#b5651d;--b-R:#2f6b4f;--grey:#d9d6cf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--b-A:#6f6c64;--b-P:#e09a5a;--b-R:#7cc39b;--grey:#3a3833}}
:root[data-theme="dark"]{--b-A:#6f6c64;--b-P:#e09a5a;--b-R:#7cc39b;--grey:#3a3833}
.sw.A{background:var(--b-A)}.sw.P{background:var(--b-P)}.sw.R{background:var(--b-R)}
.chart .b-A{fill:var(--b-A)}.chart .b-P{fill:var(--b-P)}.chart .b-R{fill:var(--b-R)}
.mt tr.cP th{box-shadow:inset 3px 0 0 var(--b-P)}.mt tr.cR th{box-shadow:inset 3px 0 0 var(--b-R)}.mt tr.cA th{box-shadow:inset 3px 0 0 var(--b-A)}
.mt.tot{max-width:560px}
.rr.cP{border-left:3px solid var(--b-P)}.rr.cR{border-left:3px solid var(--b-R)}.rr.cA{border-left:3px solid var(--b-A)}
.pairs{display:flex;gap:6px;margin:0 0 6px}.pairs button{font:600 12px "IBM Plex Mono",ui-monospace,monospace;padding:3px 10px;border-radius:4px;
border:1px solid var(--line);background:var(--card);color:var(--fg);cursor:pointer}.pairs button[aria-pressed="true"]{background:var(--acc);color:#fff;border-color:var(--acc)}
.ovscroll{max-height:75vh;overflow:auto;border:1px solid var(--line);border-radius:3px}
.ov .ovb{max-height:none;border:0;border-radius:0;background:repeating-linear-gradient(45deg,var(--grey) 0 8px,transparent 8px 16px);width:100%}
.ov .ovb img{position:absolute;top:0;left:0;width:100%;height:auto}.ov .ovb img.off{display:none}
.ov .ovb img.top{clip-path:inset(0 calc(100% - var(--pos)) 0 0);z-index:1}
.ov .ovb::after{z-index:2}.ov .tagl,.ov .tagr{z-index:3}
.sps{display:grid;gap:14px}.spr h4{margin:6px 0}.spg{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.spc{margin:0;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px;min-width:0}
.spc.P{border-top:3px solid var(--b-P)}.spc.R{border-top:3px solid var(--b-R)}
.spc figcaption{font-size:12px;margin-bottom:6px}.spi{max-height:720px;overflow:auto;border:1px solid var(--line);background:repeating-linear-gradient(45deg,var(--grey) 0 8px,transparent 8px 16px)}
.spi img{display:block;width:100%;height:auto}
.sbsv{margin:6px 0 12px}.pl{font:600 12px "IBM Plex Mono",ui-monospace,monospace;margin:6px 0 2px}
@media (max-width:640px){.spg{grid-template-columns:1fr}}
p code,li code{overflow-wrap:anywhere}
"""
JS = """document.addEventListener('input',function(e){var t=e.target;if(t.type==='range'&&t.closest('.ov')){t.closest('.ov').querySelector('.ovb').style.setProperty('--pos',t.value+'%');}});
document.addEventListener('click',function(e){var b=e.target.closest('.pairs button');if(b){var f=b.closest('.ov'),l=b.dataset.pair[0],r=b.dataset.pair[1];
f.querySelectorAll('img[data-c]').forEach(function(i){i.className=i.dataset.c===r?'base':(i.dataset.c===l?'top':'off');});
f.querySelector('.tagl').textContent=l;f.querySelector('.tagr').textContent=r;f.querySelector('.cl').textContent=l;f.querySelector('.cr').textContent=r;
f.querySelectorAll('.pairs button').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});return;}
var a=e.target.closest('a[href^="#d-"]');if(!a)return;var el=document.getElementById(a.getAttribute('href').slice(1));if(el){var d=el.closest('details');if(d)d.open=true;}});"""

if __name__ == "__main__":
    main()
