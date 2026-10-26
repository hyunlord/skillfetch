#!/usr/bin/env python3
"""Build stageQ/gallery/stageQ-gallery-v2.html from stageQ-private/gallery-data-v2.json (assemble_v2.py) and the
difference summaries stageQ-private/gallery-diffs/<task>.json (Stage Q) and stageQ1x-private/gallery-diffs/<task>.json
(Q1 extension). No new sessions. Every summary quote is checked against its source (the run's judge reason or its diff)
and the build stops if one does not match (rule kept from v1).
Page:
  top      four bar charts, one row per task, 끔 vs 켬: Claude score (mean of (p1+p2)/2), check pass rate, test functions
           added (mean per run), turns (median); then "차이 정리" per task, each quote linked to the diff row (diff
           quotes, when the line is in the side-by-side view) or to the run's row in the metrics table
  task     metrics table of every run (scores, check, tests added, README / dependency changes, files, lines, turns,
           wall, loaded skills); design: 끔|켬 overlay slider per repetition (desktop and mobile screenshots); code: the
           task's core file (the most-changed non-test, non-lock, non-README file over all its runs) as a side-by-side
           끔|켬 view per repetition, rebuilt from the start commit plus each run's hunks, syntax-highlighted at build
           time (pygments), unchanged runs collapsed; judge reasons per run, folded
Publication rules as v1 (no user paths or names; skills by name only). usage: build_gallery_v2.py"""
import base64
import difflib
import html
import io
import json
import re
import statistics as st
import subprocess
import sys
from pathlib import Path

from PIL import Image
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.token import Comment, Keyword, Literal, Name, String

E2E = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(E2E / "stage10" / "gallery"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_gallery_s10 as g  # noqa: E402
from autometrics import apply_chunk, split  # noqa: E402

OUT = E2E / "stageQ" / "gallery" / "stageQ-gallery-v2.html"
D = json.loads((E2E / "stageQ-private" / "gallery-data-v2.json").read_text())
TASKS, RUNS = D["tasks"], D["runs"]
DIFFS = {}
for d in (E2E / "stageQ-private" / "gallery-diffs", E2E / "stageQ1x-private" / "gallery-diffs"):
    if d.exists():
        DIFFS.update({p.stem: json.loads(p.read_text()) for p in d.glob("*.json")})
STACK_ORDER = ["디자인", "Rust", "Swift", "Go", "Java", "TypeScript", "Python"]
ORDER = sorted(TASKS, key=lambda t: (STACK_ORDER.index(TASKS[t]["stack"]), TASKS[t]["source"], t))
CONDN = {"off": "끔", "on": "켬"}
GPT = any("gpt" in r["scores"] for r in RUNS)
esc, S = html.escape, g.S
BUDGET = 15.0 * 1024 * 1024


def runs_of(t, c=None):
    return sorted((r for r in RUNS if r["task"] == t and (c is None or r["cond"] == c)), key=lambda r: (r["cond"] != "off", r["tag"]))


def claude(r):
    s = r["scores"]
    return (s["p1"]["score"] + s["p2"]["score"]) / 2 if "p1" in s and "p2" in s else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


# ---------------------------------------------------------------- quotes
def run_of(t, label):
    m = re.match(r"(on|off)\s+(m\d)", label.strip())
    return next((r for r in RUNS if r["task"] == t and r["cond"] == m.group(1) and r["tag"] == m.group(2)), None) if m else None


def verify_quotes():
    bad = []
    for t, d in DIFFS.items():
        for li in d["lines"]:
            for q in li["quotes"]:
                r = run_of(t, q["run"])
                src = "" if not r else (g.diff_text(r) if q["src"] == "diff" else r["reasons"].get(q["src"], {}).get("reason", ""))
                if q["quote"] not in src:
                    bad.append(f"{t} | {q['src']} {q['run']} | {q['quote'][:80]}")
    return bad


# ---------------------------------------------------------------- charts
def chart(title, unit, vals, vmax, fmtv):
    """Horizontal grouped bars: one row per task in ORDER, 끔 (muted) over 켬 (accent)."""
    row, lab, w, pad = 26, 104, 360, 30
    h = len(ORDER) * row + 34
    bw = w - lab - pad
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
        for j, c in enumerate(("off", "on")):
            v = vals[t][c]
            yy = y + j * 10
            if v is None:
                out.append(f'<text x="{lab + 2}" y="{yy + 8}" class="val">–</text>')
                continue
            ww = max(0.0, bw * v / vmax)
            out.append(f'<rect x="{lab}" y="{yy}" width="{ww:.1f}" height="8" class="b-{c}"><title>{esc(t)} {CONDN[c]} {fmtv(v)}</title></rect>'
                       f'<text x="{lab + ww + 3:.1f}" y="{yy + 7.5}" class="val">{fmtv(v)}</text>')
    out.append("</svg></figure>")
    return "".join(out)


def charts():
    def per(fn):
        return {t: {c: fn(runs_of(t, c)) for c in ("off", "on")} for t in ORDER}
    score = per(lambda rs: mean([claude(r) for r in rs]))
    check = per(lambda rs: 100 * sum(bool(r["check_pass"]) for r in rs) / len(rs) if rs else None)
    tests = per(lambda rs: mean([r["auto"]["tests_added"] for r in rs]))
    turns = per(lambda rs: st.median([r["turns"] for r in rs if r["turns"] is not None]) if rs else None)
    tmax = max([v for x in tests.values() for v in x.values() if v is not None] + [1])
    nmax = max([v for x in turns.values() for v in x.values() if v is not None] + [1])
    nice = lambda v: next(n for n in (5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100) if n >= v)  # noqa: E731
    legend = '<p class="legend"><span class="sw off"></span>끔 <span class="sw on"></span>켬</p>'
    return legend + '<div class="charts">' + "".join([
        chart("점수", "Claude (p1+p2)/2 평균, 1–5", score, 5, lambda v: f"{v:.1f}" if v % 1 else f"{v:.0f}"),
        chart("체크 통과", "%", check, 100, lambda v: f"{v:.0f}"),
        chart("추가한 테스트 함수", "실행당 평균", tests, nice(tmax), lambda v: f"{v:.1f}" if v % 1 else f"{v:.0f}"),
        chart("턴", "중앙값", turns, nice(nmax), lambda v: f"{v:.1f}" if v % 1 else f"{v:.0f}")]) + "</div>"


# ---------------------------------------------------------------- code: core file and side-by-side view
SKIP = re.compile(r"(^|/)(tests?|__tests__|spec)/|_test\.|\.test\.|\.spec\.|(^|/)test_|Tests?\.(java|swift)$|(^|/)README|"
                  r"\.(lock|lockb|svg|png|ico|snap|csv|json)$|(^|/)(go\.sum|Cargo\.lock|package-lock\.json|uv\.lock)$")


def core_file(t):
    tot = {}
    for r in runs_of(t):
        for f, ch in split(g.diff_text(r)).items():
            if SKIP.search(f):
                continue
            tot[f] = tot.get(f, 0) + sum(1 for l in ch.split("\n") if l[:1] in "+-" and l[:3] not in ("+++", "---"))
    return max(tot, key=tot.get) if tot else None


def base_text(t, path):
    p = subprocess.run(["git", "-C", str(E2E / "repos" / TASKS[t]["repo"]), "show", f"{TASKS[t]['base_branch']}:{path}"],
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ""


def final_text(r, path, base):
    ch = split(g.diff_text(r)).get(path)
    if ch is None:
        return base
    return apply_chunk(base, ch) or ""


CLS = [(Comment, "c"), (String, "s"), (Literal.Number, "m"), (Keyword, "k"), (Name.Function, "f"), (Name.Class, "f"),
       (Name.Decorator, "k"), (Name.Builtin, "b")]


def highlight(text, path):
    try:
        lexer = get_lexer_for_filename(path, stripnl=False, ensurenl=False)
    except Exception:  # noqa: BLE001
        lexer = TextLexer(stripnl=False, ensurenl=False)
    lines, cur = [], []
    for tok, val in lexer.get_tokens(text):
        cls = next((c for tt, c in CLS if tok in tt), None)
        parts = val.split("\n")
        for k, part in enumerate(parts):
            if k:
                lines.append("".join(cur))
                cur = []
            if part:
                e = esc(g.scrub(part))
                cur.append(f'<span class="{cls}">{e}</span>' if cls else e)
    lines.append("".join(cur))
    return lines


def side_by_side(t, tag, path, anchor):
    """Rows for the 끔|켬 view of `path` for repetition `tag`; returns (html, {row id: plain text of both sides})."""
    off = next((r for r in runs_of(t, "off") if r["tag"] == tag), None)
    on = next((r for r in runs_of(t, "on") if r["tag"] == tag), None)
    if not off or not on:
        return "", {}
    base = base_text(t, path)
    a, b = final_text(off, path, base), final_text(on, path, base)
    al, bl = a.split("\n"), b.split("\n")
    ah, bh = highlight(a, path), highlight(b, path)
    rows, texts, n = [], {}, 0

    def row(i, j, kind):
        nonlocal n
        n += 1
        rid = f"{anchor}-L{n}"
        texts[rid] = (al[i] if i is not None else "") + "\n" + (bl[j] if j is not None else "")
        lc = f'<td class="ln">{i + 1}</td><td class="code {kind if i is not None else "pad"}">{ah[i] if i is not None else ""}</td>' if i is not None else '<td class="ln"></td><td class="code pad"></td>'
        rc = f'<td class="ln">{j + 1}</td><td class="code {kind if j is not None else "pad"}">{bh[j] if j is not None else ""}</td>' if j is not None else '<td class="ln"></td><td class="code pad"></td>'
        rows.append(f'<tr id="{rid}">{lc}{rc}</tr>')

    sm = difflib.SequenceMatcher(None, al, bl, autojunk=False)
    ops = sm.get_opcodes()
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
            hidden = span - keep_head - keep_tail
            rows.append(f'<tr class="fold"><td colspan="4">… 같은 줄 {hidden}개 …</td></tr>')
            for k in range(span - keep_tail, span):
                row(i1 + k, j1 + k, "eq")
        else:
            for k in range(max(i2 - i1, j2 - j1)):
                i = i1 + k if k < i2 - i1 else None
                j = j1 + k if k < j2 - j1 else None
                row(i, j, "chg" if i is not None and j is not None else ("del" if i is not None else "add"))
    same = a == b
    head = (f'<div class="sbs-h"><span>끔 {esc(tag)} · {len(al)}줄</span><span>켬 {esc(tag)} · {len(bl)}줄</span></div>')
    body = ('<p class="sm">두 결과의 이 파일이 같다.</p>' if same else
            f'<div class="tw sbs-w"><table class="sbs"><colgroup><col class="lnc"><col><col class="lnc"><col></colgroup>'
            f'{"".join(rows)}</table></div>')
    return head + body, texts


# ---------------------------------------------------------------- design: overlay slider
def encode(png, scale, q):
    im = Image.open(png)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=q, method=6)
    return buf.getvalue(), im.size


def images():
    pngs = sorted({p for r in RUNS if r["bundle"] == 1 for sub in ("screens", "screens-375") for p in r["shots"].get(sub, [])[:1]})
    for scale, q in ((1.0, 70), (0.85, 64), (0.7, 58), (0.55, 52)):
        enc = {p: encode(p, scale, q) for p in pngs}
        total = sum(len(b) * 4 / 3 for b, _ in enc.values())
        if total < BUDGET - 4 * 1024 * 1024:
            return {p: (f"data:image/webp;base64,{base64.b64encode(b).decode()}", sz) for p, (b, sz) in enc.items()}, scale, q
    raise SystemExit("images do not fit the budget")


def slider(t, tag, imgs, sid):
    off = next((r for r in runs_of(t, "off") if r["tag"] == tag), None)
    on = next((r for r in runs_of(t, "on") if r["tag"] == tag), None)
    out = []
    for sub, lab in (("screens", "데스크톱"), ("screens-375", "모바일 375")):
        a = (off or {}).get("shots", {}).get(sub, [])
        b = (on or {}).get("shots", {}).get(sub, [])
        if not a or not b or a[0] not in imgs or b[0] not in imgs:
            out.append(f'<div class="none">{lab}: 스크린샷 없음</div>')
            continue
        (ua, (w, h)), (ub, _) = imgs[a[0]], imgs[b[0]]
        iid = f"{sid}-{'d' if sub == 'screens' else 'm'}"
        out.append(f'<figure class="ov {"mob" if sub != "screens" else ""}"><div class="ovb" style="--pos:50%">'
                   f'<img src="{ub}" alt="{esc(t)} 켬 {esc(tag)} {lab}" width="{w}" height="{h}">'
                   f'<img class="top" src="{ua}" alt="{esc(t)} 끔 {esc(tag)} {lab}" width="{w}" height="{h}">'
                   f'<span class="tagl">끔</span><span class="tagr">켬</span></div>'
                   f'<label class="sr" for="{iid}">{lab} 끔/켬 경계</label><input id="{iid}" type="range" min="0" max="100" value="50">'
                   f'<figcaption>{lab} · 왼쪽 끔, 오른쪽 켬 · {w}×{h}</figcaption></figure>')
    return '<div class="ovs">' + "".join(out) + "</div>"


# ---------------------------------------------------------------- tables and summaries
def metrics_table(t):
    head = ("<tr><th>실행</th><th>p1 / p2" + (" / GPT" if GPT else "") + "</th><th>체크</th><th>추가 테스트</th><th>README</th>"
            "<th>의존성</th><th>파일</th><th>+ / −</th><th>턴</th><th>벽시계</th><th>로드한 스킬</th></tr>")
    rows = []
    for r in runs_of(t):
        s, a = r["scores"], r["auto"]
        sc = " / ".join(str(s[p]["score"]) if p in s else "–" for p in (("p1", "p2", "gpt") if GPT else ("p1", "p2")))
        chk = '<span class="ok">통과</span>' if r["check_pass"] else ('<span class="bad">실패</span>' if r["check_pass"] is False else "–")
        rows.append(f'<tr id="r-{t}-{r["cond"]}-{r["tag"]}"><th>{CONDN[r["cond"]]} {esc(r["tag"])}</th><td class="num">{sc}</td><td>{chk}</td>'
                    f'<td class="num">{a["tests_added"]}</td><td>{"바꿈" if a["readme"] else "–"}</td>'
                    f'<td>{S(", ".join(a["deps"])) or "–"}</td><td class="num">{a["files"]}</td><td class="num">+{a["added"]} −{a["deleted"]}</td>'
                    f'<td class="num">{g.fmt(r["turns"])}</td><td class="num">{g.fmt(r["wall_s"], 0)}초</td>'
                    f'<td>{S(", ".join(g.short(x) for x in r["loaded"])) or "–"}</td></tr>')
    return f'<div class="tw"><table class="mt"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div>'


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
                body = q["quote"].lstrip("+- ")
                hit = next((rid for rid, txt in row_texts.get((t, r["tag"]), {}).items() if body and body in txt), None)
                if hit:
                    target = f"#{hit}"
            lab = esc(q["run"].replace("on", "켬").replace("off", "끔"))
            qs.append(f'<li><a class="src" href="{target}">{esc(q["src"])} · {lab}</a> <q>{S(q["quote"])}</q></li>')
        lines.append(f'<li><p>{S(li["text"])}</p><ul class="qs">{"".join(qs)}</ul></li>')
    return (f'<div class="sb" id="sum-{t}"><div class="sbh"><h4><a href="#t-{t}">{esc(t)}</a></h4>'
            f'<span class="pill {"same" if d["verdict"] == "차이 없음" else "diff"}">{esc(d["verdict"])}</span>'
            f'<span class="sm">{esc(TASKS[t]["stack"])} · {"Stage Q" if TASKS[t]["source"] == "Q" else "Q1 확장"}</span></div>'
            f'<ol class="dl">{"".join(lines)}</ol></div>')


def reasons_block(t):
    items = []
    for r in runs_of(t):
        rs = r["reasons"]
        ps = "".join(f'<p class="why"><b>{p}</b> {S(rs[p]["reason"])}</p>' for p in ("p1", "p2", "gpt") if p in rs)
        items.append(f'<div class="rr"><h5>{CONDN[r["cond"]]} {esc(r["tag"])}</h5>{ps}</div>')
    return f'<details class="rsn"><summary>실행별 판정 근거</summary><div class="rrs">{"".join(items)}</div></details>'


def main():
    bad = verify_quotes()
    if bad:
        print(json.dumps({"unverified_quotes": bad}, ensure_ascii=False, indent=1))
        raise SystemExit("summaries not ready")
    imgs, scale, q = images()
    sections, row_texts = [], {}
    for t in ORDER:
        tags = sorted({r["tag"] for r in runs_of(t)})
        parts = [f'<div class="task" id="t-{t}"><h3>{esc(t)} <span class="sm">{esc(TASKS[t]["stack"])} · '
                 f'{"Stage Q" if TASKS[t]["source"] == "Q" else "Q1 확장"}</span> <a class="up" href="#sum-{t}">차이 정리로</a></h3>',
                 f'<details class="prompt"><summary>요청 원문</summary><p>{S(TASKS[t]["prompt"])}</p></details>', metrics_table(t)]
        if TASKS[t]["bundle"] == 1:
            for k, tag in enumerate(tags):
                parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>끔 {tag} | 켬 {tag}</summary>{slider(t, tag, imgs, f"s-{t}-{tag}")}</details>')
        else:
            cf = core_file(t)
            if cf:
                parts.append(f'<p class="cf">핵심 파일 <code>{S(cf)}</code></p>')
                for k, tag in enumerate(tags):
                    h, texts = side_by_side(t, tag, cf, f"d-{t}-{tag}")
                    row_texts[(t, tag)] = texts
                    parts.append(f'<details class="pair" {"open" if k == 0 else ""}><summary>끔 {tag} | 켬 {tag}</summary>{h}</details>')
        parts.append(reasons_block(t))
        parts.append("</div>")
        sections.append("".join(parts))
    summ = '<div class="sgrid">' + "".join(summary_block(t, row_texts) for t in ORDER) + "</div>"
    n_q = sum(r["source"] == "Q" for r in RUNS)
    head = f"""<header class="wrap"><p class="eyebrow">skillfetch e2e · Stage Q</p><h1>켜기/끄기 갤러리 v2</h1>
<p><b>켬</b> 라우터 S-b′ + skillfetch MCP(index-staging-4) · <b>끔</b> 라우터·MCP 없음. 환경은 E1이다. Stage Q 태스크 6개(2회, 실행 {n_q}개)와 Q1 확장 태스크 12개(3회, 실행 {len(RUNS) - n_q}개)가 있다.</p>
<p>점수는 1–5 블라인드 판정(Claude p1, p2{", GPT" if GPT else ""})이다. 추가 테스트, README, 의존성, 파일·줄 수는 diff에서 자동으로 셌다.
"차이 정리"의 각 줄에는 판정 근거나 diff에서 그대로 옮긴 인용을 붙였다. 빌드 때 원문과 대조했고, 인용을 누르면 해당 diff 줄이나 실행 행으로 간다.</p>
<p class="sm">코드 태스크는 핵심 파일 하나를 끔|켬 나란히 보인다(시작 커밋에 각 실행의 변경을 적용해 다시 만듦, 같은 줄은 접음). 디자인은 슬라이더로 끔·켬 화면을 겹쳐 본다. 스크린샷은 크기 {int(scale * 100)}%, WebP {q}로 다시 인코딩했다.</p></header>"""
    nav = '<nav class="wrap"><a href="#charts">차트</a><a href="#summary">차이 정리</a>' + "".join(
        f'<a href="#t-{t}">{esc(t)}</a>' for t in ORDER) + "</nav>"
    doc = (f'<title>켜기/끄기 갤러리 v2</title><link rel="preconnect" href="https://fonts.googleapis.com">'
           f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">'
           f'<style>{g.CSS}{CSS}</style>{head}{nav}<main class="wrap">'
           f'<section id="charts"><h2>태스크별 끔 vs 켬</h2>{charts()}</section>'
           f'<section id="summary"><h2>차이 정리</h2>{summ}</section><section>{"".join(sections)}</section></main><script>{JS}</script>')
    for pat in (r"/Users/", r"\b<user>\b", r"skillfetch-e2e-wt", r"/private/tmp"):
        assert not re.search(pat, doc), f"publication rule: {pat} present"
    OUT.write_text(doc)
    size = OUT.stat().st_size
    print(json.dumps({"bytes": size, "MB": round(size / 1024 / 1024, 2), "runs": len(RUNS), "tasks": len(ORDER), "image_scale": scale,
                      "webp_q": q, "gpt": GPT, "summaries": len(DIFFS), "missing_summaries": [t for t in ORDER if t not in DIFFS]}, ensure_ascii=False))
    assert size < 16 * 1024 * 1024


CSS = """
:root{--b-off:#9aa79c;--b-on:#2f6b4f;--sx-k:#7a3e9d;--sx-s:#a15c00;--sx-c:#6b736a;--sx-m:#0b6e99;--sx-f:#1f5fa8;--sx-b:#8a4b2a;--chg:#fff4d6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--b-off:#5f6b61;--b-on:#7cc39b;--sx-k:#c79bf2;--sx-s:#f0b366;--sx-c:#8c958a;--sx-m:#6fc3e8;--sx-f:#8ab4f8;--sx-b:#e3a07e;--chg:#3a3218}}
:root[data-theme="dark"]{--b-off:#5f6b61;--b-on:#7cc39b;--sx-k:#c79bf2;--sx-s:#f0b366;--sx-c:#8c958a;--sx-m:#6fc3e8;--sx-f:#8ab4f8;--sx-b:#e3a07e;--chg:#3a3218}
.legend{display:flex;gap:6px 14px;align-items:center;font-size:12px;color:var(--mut);margin:4px 0 8px}.sw{display:inline-block;width:12px;height:8px;border-radius:2px;margin-right:4px}.sw.off{background:var(--b-off)}.sw.on{background:var(--b-on)}
.charts{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:14px}
.chart{margin:0;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:10px 10px 4px}.chart figcaption{font-weight:600;font-size:13px;margin-bottom:4px}
.chart svg{width:100%;height:auto;display:block}.chart .grid{stroke:var(--line);stroke-width:1}.chart .tick,.chart .val{font:10px "IBM Plex Mono",ui-monospace,monospace;fill:var(--mut)}
.chart .lab{font:11px "IBM Plex Mono",ui-monospace,monospace;fill:var(--fg)}.chart .b-off{fill:var(--b-off)}.chart .b-on{fill:var(--b-on)}
a.src{text-decoration:none}a.src:hover{text-decoration:underline}
table.mt{border-collapse:collapse;font-size:12px;width:100%;margin:6px 0 10px}.mt th,.mt td{border-top:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
.mt thead th{color:var(--mut);font-weight:600;white-space:nowrap;border-top:0}.mt tbody th{white-space:nowrap}.mt tr:target{background:var(--acc2)}
.cf{font-size:12px;color:var(--mut);margin:8px 0 4px}details.pair{margin:6px 0}details.pair>summary{font-weight:600}
.sbs-h{display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:11px;color:var(--mut);margin:6px 0 2px}
.sbs-w{max-height:640px;overflow:auto;border:1px solid var(--line);border-radius:4px}
table.sbs{border-collapse:collapse;width:100%;table-layout:fixed;font:11px/1.5 "IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
.sbs col.lnc{width:3.6em}.sbs td{vertical-align:top;padding:0 6px;white-space:pre-wrap;overflow-wrap:anywhere}.sbs td.ln{color:var(--mut);text-align:right;user-select:none;padding-right:4px;border-right:1px solid var(--line)}
.sbs td.chg{background:var(--chg)}.sbs td.add{background:var(--add)}.sbs td.del{background:var(--del)}.sbs td.pad{background:var(--code)}
.sbs tr.fold td{text-align:center;color:var(--mut);background:var(--code);font-size:10px;padding:2px}.sbs tr:target td{outline:2px solid var(--acc);outline-offset:-2px}
.sbs .k{color:var(--sx-k)}.sbs .s{color:var(--sx-s)}.sbs .c{color:var(--sx-c);font-style:italic}.sbs .m{color:var(--sx-m)}.sbs .f{color:var(--sx-f)}.sbs .b{color:var(--sx-b)}
.ovs{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}.ov{margin:0;flex:1 1 420px;min-width:0}.ov.mob{flex:0 1 220px}
.ovb{position:relative;border:1px solid var(--line);border-radius:3px;overflow:hidden;background:#fff;max-height:560px}
.ovb img{display:block;width:100%;height:auto}.ovb img.top{position:absolute;inset:0;clip-path:inset(0 calc(100% - var(--pos)) 0 0)}
.ovb::after{content:"";position:absolute;top:0;bottom:0;left:var(--pos);width:2px;background:var(--acc);pointer-events:none}
.tagl,.tagr{position:absolute;top:6px;font:600 11px "IBM Plex Sans KR",sans-serif;padding:1px 6px;border-radius:3px;background:rgba(0,0,0,.6);color:#fff}.tagl{left:6px}.tagr{right:6px}
.ov input[type=range]{width:100%;accent-color:var(--acc);margin:6px 0 0}.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.rrs{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:8px}.rr{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:8px}
.rsn{margin-top:8px}
"""
JS = """document.addEventListener('input',function(e){var t=e.target;if(t.type==='range'&&t.closest('.ov')){t.closest('.ov').querySelector('.ovb').style.setProperty('--pos',t.value+'%');}});
document.addEventListener('click',function(e){var a=e.target.closest('a[href^="#d-"]');if(!a)return;var el=document.getElementById(a.getAttribute('href').slice(1));if(el){var d=el.closest('details');if(d)d.open=true;}});"""

if __name__ == "__main__":
    main()
