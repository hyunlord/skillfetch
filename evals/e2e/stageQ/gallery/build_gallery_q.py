#!/usr/bin/env python3
"""Build stageQ/gallery/stageQ-gallery.html (Q1, DESIGN §1) from existing Stage Q outputs only (no new sessions).

Input: stageQ-private/gallery-data.json (assemble_q.py) and the per-task difference summaries
(stageQ-private/gallery-diffs/<task>.json: lines with verbatim quotes from judge reasons or diffs; every quote is checked
against its source here and the build stops if one does not match).
Top: "차이 정리" per task (켬 / 끔) with a table of Claude (and GPT when present) scores, checks, loaded skills, median
turns and median wall time. Body: every Q1 run (6 tasks × 켬·끔 × m1, m2). Design runs: desktop and mobile screenshots
(WebP data URIs); code runs: changed files, a diff excerpt (≤ 30 lines), check items, loaded skills, turns, scores, reasons.
Same publication rules and page style as stage10/gallery/build_gallery_s10.py (helpers imported from it).
usage: build_gallery_q.py"""
import html
import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

E2E = Path(__file__).resolve().parents[2]
PRIV = E2E / "stageQ-private"
OUT = E2E / "stageQ" / "gallery" / "stageQ-gallery.html"
sys.path.insert(0, str(E2E / "stage10" / "gallery"))
import build_gallery_s10 as g  # noqa: E402

esc, S, fmt = html.escape, g.S, g.fmt
D = json.loads((PRIV / "gallery-data.json").read_text())
TASKS, RUNS = D["tasks"], D["runs"]
DIFFS = {p.stem: json.loads(p.read_text()) for p in (PRIV / "gallery-diffs").glob("*.json")}
ORDER = ["d1-landing", "d4-email", "s10-t016", "s11-t266", "s2-api", "s2-data"]
GROUP = {"d1-landing": "디자인", "d4-email": "디자인", "s10-t016": "새로 커버된 비 Python", "s11-t266": "새로 커버된 비 Python",
         "s2-api": "일반 코딩", "s2-data": "일반 코딩"}
CONDN = {"on": "켬", "off": "끔"}
GPT = any("gpt" in r["scores"] for r in RUNS)


def run_of(task, label):
    m = re.match(r"(on|off)\s+(m\d)", label.strip())
    return next((r for r in RUNS if r["task"] == task and r["cond"] == m.group(1) and r["tag"] == m.group(2)), None) if m else None


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


def runs_of(task, cond):
    return sorted((r for r in RUNS if r["task"] == task and r["cond"] == cond), key=lambda r: r["tag"])


def claude(r):
    return (r["scores"]["p1"]["score"] + r["scores"]["p2"]["score"]) / 2


def loaded_txt(rs):
    c = Counter(g.short(x) for r in rs for x in r["loaded"])
    return ", ".join(f"{k} ×{v}" if v > 1 else k for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))) or "없음"


def check_txt(r):
    if r["check_pass"]:
        return '<span class="ok">통과</span>'
    bad = [i["name"] for i in r["check_items"] if i["pass"] is False]
    return '<span class="bad">실패</span>: ' + S(", ".join(bad[:3]))


def card(r, imgs):
    s = r["scores"]
    title = f'{CONDN[r["cond"]]} · {esc(r["tag"])}'
    sc = f'{s["p1"]["score"]} / {s["p2"]["score"]}' + (f' / {s["gpt"]["score"]}' if GPT else "")
    rows = [("판정 p1 / p2" + (" / GPT" if GPT else ""), sc)]
    if r["bundle"] == 1:
        rows.append(("AI 템플릿 p1 / p2", f'{s["p1"]["ai_look"]} / {s["p2"]["ai_look"]}'))
    files = r["diff"].get("files", [])
    rows += [("로드한 스킬", S(loaded_txt([r])) + ("" if r["loaded"] or not r["fired"] else " (검색만)")),
             ("턴 · 벽시계", f'{fmt(r["turns"])} · {fmt(r["wall_s"], 0)}초'), ("체크", check_txt(r)),
             ("변경", f'파일 {len(files)}개 · +{r["diff"].get("added", 0)} / −{r["diff"].get("deleted", 0)}')]
    if r["bundle"] == 1:
        figs = []
        for sub, lab in (("screens", "데스크톱"), ("screens-375", "모바일 375")):
            ps = r["shots"].get(sub, [])
            if ps and ps[0] in imgs:
                uri, (w, h) = imgs[ps[0]]
                figs.append(f'<figure><img loading="lazy" src="{uri}" data-full="1" alt="{esc(r["task"])} {title} {lab}" width="{w}" height="{h}"><figcaption>{lab} · {w}×{h}</figcaption></figure>')
        body = f'<div class="shots">{"".join(figs)}</div>' if figs else '<div class="none">스크린샷 없음</div>'
    else:
        f, ex = g.excerpt(r)
        flist = "".join(f'<li><code>{S(x["file"])}</code> <span class="num">+{x["added"]} −{x["deleted"]}</span></li>' for x in files[:12])
        more = f"<li>… 외 {len(files) - 12}개</li>" if len(files) > 12 else ""
        body = f'<ul class="files">{flist}{more}</ul>' if files else '<p class="sm">변경 없음</p>'
        if ex:
            body += f'<details class="dx"><summary>핵심 diff · <code>{S(f)}</code></summary><pre class="diff">{g.diff_html(ex)}</pre></details>'
        if r["check_items"]:
            body += "<details><summary>체크 항목</summary><table class=\"ct\">" + "".join(
                f'<tr><td class="{"ok" if i["pass"] else ("bad" if i["pass"] is False else "na")}">{"✓" if i["pass"] else ("✗" if i["pass"] is False else "·")}</td><td>{S(i["name"])}</td></tr>'
                for i in r["check_items"]) + "</table></details>"
    rs = r["reasons"]
    reason = f'<p class="why"><b>p1</b> {S(rs["p1"]["reason"])}</p><details><summary>p2' + (" · GPT" if GPT else "") + \
        f' 근거</summary><p class="why"><b>p2</b> {S(rs["p2"]["reason"])}</p>' + \
        (f'<p class="why"><b>GPT</b> {S(rs["gpt"]["reason"])}</p>' if GPT else "") + "</details>"
    dl = "<dl>" + "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>"
    return f'<article class="run"><h5>{title}</h5>{body}{dl}{reason}</article>'


def summary_table(task):
    rows = []
    for c in ("off", "on"):
        rs = runs_of(task, c)
        gpt = f"<td class=\"num\">{statistics.mean(r['scores']['gpt']['score'] for r in rs):.2f}</td>" if GPT else ""
        rows.append(f"<tr><th>{CONDN[c]}</th><td class=\"num\">{statistics.mean(claude(r) for r in rs):.2f}</td>{gpt}"
                    f"<td class=\"num\">{sum(bool(r['check_pass']) for r in rs)}/{len(rs)}</td>"
                    f"<td>{S(loaded_txt(rs))}</td><td class=\"num\">{fmt(statistics.median(r['turns'] for r in rs), 1)}</td>"
                    f"<td class=\"num\">{fmt(statistics.median(r['wall_s'] for r in rs), 0)}초</td></tr>")
    return ('<div class="tw"><table class="sum"><thead><tr><th></th><th>Claude</th>' + ("<th>GPT</th>" if GPT else "") +
            '<th>체크</th><th>로드한 스킬</th><th>중앙 턴</th><th>중앙 벽시계</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def summary_block(task):
    d = DIFFS[task]
    lines = []
    for li in d["lines"]:
        qs = "".join(f'<li><span class="src">{esc(q["src"])} · {esc(q["run"].replace("on", "켬").replace("off", "끔"))}</span> <q>{S(q["quote"])}</q></li>' for q in li["quotes"])
        lines.append(f'<li><p>{S(li["text"])}</p><ul class="qs">{qs}</ul></li>')
    return (f'<div class="sb" id="sum-{task}"><div class="sbh"><h4><a href="#t-{task}">{esc(task)}</a></h4>'
            f'<span class="pill {"same" if d["verdict"] == "차이 없음" else "diff"}">{esc(d["verdict"])}</span><span class="sm">{esc(GROUP[task])}</span></div>'
            f'<ol class="dl">{"".join(lines)}</ol>{summary_table(task)}</div>')


def main():
    bad = verify_quotes()
    missing = [t for t in ORDER if t not in DIFFS]
    if bad or missing:
        print(json.dumps({"unverified_quotes": bad, "missing_summaries": missing}, ensure_ascii=False, indent=1))
        raise SystemExit("summaries not ready")
    g.RUNS = RUNS  # choose_images() reads the module's RUNS
    imgs, scale, q = g.choose_images()
    summ = '<div class="sgrid">' + "".join(summary_block(t) for t in ORDER) + "</div>"
    body = ""
    for t in ORDER:
        body += f'<div class="task" id="t-{t}"><h3>{esc(t)} <span class="sm">{esc(GROUP[t])}</span> <a class="up" href="#sum-{t}">차이 정리로</a></h3>'
        body += f'<details class="prompt"><summary>요청 원문</summary><p>{S(TASKS[t]["prompt"])}</p></details>'
        for c in ("off", "on"):
            body += f'<div class="cond"><h4>{CONDN[c]}</h4><div class="runs">' + "".join(card(r, imgs) for r in runs_of(t, c)) + "</div></div>"
        body += "</div>"
    judges = "Claude 두 패스(p1, p2)" + ("와 GPT" if GPT else "")
    head = f"""<header class="wrap"><p class="eyebrow">skillfetch e2e · Stage Q</p><h1>Stage Q 켜기/끄기 갤러리</h1>
<p><b>켬</b> 라우터 S-b′ + skillfetch MCP(index-staging-4) · <b>끔</b> 라우터·MCP 없음. 환경은 프로젝트 설정만(E1). 태스크 6개 × 조건 2개 × 2회(m1, m2), 실행 {len(RUNS)}개가 모두 있다.</p>
<p>점수는 1–5 블라인드 판정({judges}). 디자인은 "쓸만함", 그 밖은 "총점". 표의 Claude는 실행별 (p1+p2)/2의 평균이다. 체크는 객관 체크 통과 수, 중앙 턴·벽시계는 2회의 중앙값이다.
"차이 정리"의 각 줄에는 판정자 근거나 diff에서 그대로 옮긴 인용을 붙였다. 빌드 때 원문과 대조했고, 근거가 없는 줄은 쓰지 않았다.</p>
<p class="sm">스크린샷은 체크가 찍은 화면(데스크톱, 모바일 375px)을 크기 {int(scale * 100)}%, WebP 품질 {q}로 다시 인코딩했다. 썸네일을 누르면 크게 보인다. 경로와 사용자 이름은 지웠고, 스킬은 이름만 적었다.</p></header>"""
    nav = '<nav class="wrap"><a href="#summary">차이 정리</a>' + "".join(f'<a href="#t-{t}">{esc(t)}</a>' for t in ORDER) + "</nav>"
    doc = (f'<title>Stage Q 갤러리</title><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&display=swap"><style>{g.CSS}</style>{head}{nav}'
           f'<main class="wrap"><section id="summary"><h2>차이 정리</h2><p class="intro">켬과 끔이 실제로 어디가 다른지 적었다. 근거로 확인되지 않으면 "차이 없음"이다.</p>{summ}</section><section>{body}</section></main>'
           f'<div id="ov" hidden><span class="cap"></span><img alt=""></div><script>{g.JS}</script>')
    for pat in (r"/Users/", r"\b<user>\b", r"skillfetch-e2e-wt", r"/private/tmp"):
        assert not re.search(pat, doc), f"publication rule: {pat} present"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc)
    size = OUT.stat().st_size
    print(json.dumps({"bytes": size, "MB": round(size / 1024 / 1024, 2), "runs": len(RUNS), "image_scale": scale, "webp_q": q,
                      "gpt": GPT, "summaries": {t: DIFFS[t]["verdict"] for t in ORDER}}, ensure_ascii=False))
    assert size < 16 * 1024 * 1024


if __name__ == "__main__":
    main()
