"""Draw the four figures of the launch post (docs/writeup/post-ko.md, post-en.md) into
docs/writeup/img/ as PNG (white background, 200 dpi), Korean and English labels separately.

Every number drawn comes from the tables below. Each entry gives the number as written in its
source, the source (`§N` = docs/writeup/numbers.md section N; `post` = both posts) and a line
fragment that holds it; tests/test_post_figures.py checks that each fragment is in that source.
Figures do not change any number; derived values (sums, shares, 30 − fired) are computed here.

Run from the repo root:  uv run --with matplotlib python scripts/make_post_figures.py
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "writeup" / "img"
LANGS = ("ko", "en")


class Num(NamedTuple):
    raw: str  # the number as written in the source
    src: str  # "§N" (numbers.md section) or "post"
    where: str  # fragment of the source that contains raw (for "post": post-ko.md)
    where_en: str = ""  # "post" only: fragment of post-en.md


def val(n: Num) -> float:
    return float(n.raw.rstrip("%").replace(",", "").split("/")[0])


def frac(n: Num) -> tuple[int, int]:
    a, b = n.raw.strip("*").split("/")
    return int(a), int(b)


# (1) Licenses, numbers.md §2
LICENSE_TOTAL = Num("1831", "§1", "Skills discovered: **1831**")
LICENSE = [  # (key, skills, share)
    (
        "explicit",
        Num("377", "§2", "| explicit | 367 | 0 | 10 | 0 | 0 | 377 | 20.6% |"),
        Num("20.6%", "§2", "| 377 | 20.6% |"),
    ),
    (
        "upstream_no_license",
        Num("824", "§2", "| upstream_no_license | 0 | 0 | 0 | 0 | 824 |"),
        Num("45.0%", "§2", "| 824 | 824 | 45.0% |"),
    ),
    (
        "upstream_unknown",
        Num("630", "§2", "| upstream_unknown | 0 | 0 | 0 | 0 | 630 |"),
        Num("34.4%", "§2", "| 630 | 630 | 34.4% |"),
    ),
]
LICENSE_PERMISSIVE = Num("367", "§2", "| explicit | 367 |")
LICENSE_PROPRIETARY = Num("10", "§2", "| explicit | 367 | 0 | 10 |")

# (2) top: judge verdicts over the open pairs, numbers.md §5
JUDGE_TOTAL = Num("2011", "§5", "Pairs judged: 2011")
JUDGE = [  # (key, pairs...); error and unclear are drawn as one bar, as in the post
    ("independent", [Num("1666", "§5", "| independent | 1666 | 82.8% |")]),
    ("situational", [Num("191", "§5", "| situational | 191 | 9.5% |")]),
    ("conflict", [Num("90", "§5", "| conflict | 90 | 4.5% |")]),
    ("carve_out", [Num("57", "§5", "| carve_out | 57 | 2.8% |")]),
    (
        "error_unclear",
        [Num("6", "§5", "| error | 6 | 0.3% |"), Num("1", "§5", "| unclear | 1 | 0.0% |")],
    ),
]
JUDGE_SHARE = {  # share as printed in §5; error + unclear (7/2011) rounds to error's 0.3%
    "independent": Num("82.8%", "§5", "| 1666 | 82.8% |"),
    "situational": Num("9.5%", "§5", "| 191 | 9.5% |"),
    "conflict": Num("4.5%", "§5", "| 90 | 4.5% |"),
    "carve_out": Num("2.8%", "§5", "| 57 | 2.8% |"),
    "error_unclear": Num("0.3%", "§5", "| error | 6 | 0.3% |"),
}

# (2) bottom: runs that followed the named winner, numbers.md §8-§10 (260 runs per method)
WINNER = [  # (key, controlled runs per order: A named, B named)
    ("header", [Num("**112/260**", "§8", "**112/260** of all runs")]),
    ("block", [Num("**145/260**", "§9", "**145/260** of all runs")]),
    (
        "strip",
        [
            Num("51/130", "§10", "| strip: `strip-a` | 130 | 51/130 (0.39)"),
            Num("69/130", "§10", "| strip: `strip-b` | 130 | 69/130 (0.53)"),
        ],
    ),
]
WINNER_RANGE = Num("43–56%", "post", "지정한 스킬을 따른 실행은 43–56%다", "43–56% of runs")

# (3) task types: score per condition and median turns, numbers.md §11 (stage 2; design =
# landing pages in the 1b rejudge; router = C2, after the search fix)
TASKS = [  # (key, score A / B / router, median turns A, router)
    (
        "design",
        [
            Num("3.50", "§11", "| landing page (1b) | A | 4 | 3.50 |"),
            Num("4.75", "§11", "| landing page (1b) | B | 4 | 4.75 |"),
            Num("4.75", "§11", "| landing page (1b) | C2 | 4 | 4.75 |"),
        ],
        [
            Num("19.5", "§11", "| A | 3.50 | 2.00 | 0.36 | 19.5 |"),
            Num("26.5", "§11", "| C2, search k=50 | 4.75 | 0.50 | 0.71 | 26.5 |"),
        ],
    ),
    (
        "tests",
        [
            Num("4.90", "§11", "| test writing | A | 5 | 4.90 (5.00 / 4.80) |"),
            Num("5.00", "§11", "| test writing | B | 5 | 5.00 (5.00 / 5.00) |"),
            Num("5.00", "§11", "| test writing | C2 | 5 | 5.00 (5.00 / 5.00) |"),
        ],
        [
            Num("10", "§11", "| test writing | A | 5 | 4.90 (5.00 / 4.80) | 5/5 | 10 |"),
            Num("16", "§11", "| test writing | C2 | 5 | 5.00 (5.00 / 5.00) | 5/5 | 16 |"),
        ],
    ),
    (
        "api",
        [
            Num("4.20", "§11", "| backend API | A | 5 | 4.20 (4.20 / 4.20) |"),
            Num("4.20", "§11", "| backend API | B | 5 | 4.20 (4.40 / 4.00) |"),
            Num("4.80", "§11", "| backend API | C2 | 5 | 4.80 (4.80 / 4.80) |"),
        ],
        [
            Num("15", "§11", "| backend API | A | 5 | 4.20 (4.20 / 4.20) | 5/5 | 15 |"),
            Num("23", "§11", "| backend API | C2 | 5 | 4.80 (4.80 / 4.80) | 5/5 | 23 |"),
        ],
    ),
    (
        "docs",
        [
            Num("4.10", "§11", "| documentation | A | 5 | 4.10 (4.00 / 4.20) |"),
            Num("4.70", "§11", "| documentation | B | 5 | 4.70 (4.80 / 4.60) |"),
            Num("4.40", "§11", "| documentation | C2 | 5 | 4.40 (4.40 / 4.40) |"),
        ],
        [
            Num("10", "§11", "| documentation | A | 5 | 4.10 (4.00 / 4.20) | 5/5 | 10 |"),
            Num("17", "§11", "| documentation | C2 | 5 | 4.40 (4.40 / 4.40) | 5/5 | 17 |"),
        ],
    ),
    (
        "data",
        [
            Num("4.50", "§11", "| data script | A | 5 | 4.50 (4.60 / 4.40) |"),
            Num("4.50", "§11", "| data script | B | 5 | 4.50 (5.00 / 4.00) |"),
            Num("4.50", "§11", "| data script | C2 | 5 | 4.50 (4.60 / 4.40) |"),
        ],
        [
            Num("12", "§11", "| data script | A | 5 | 4.50 (4.60 / 4.40) | 5/5 | 12 |"),
            Num("18", "§11", "| data script | C2 | 5 | 4.50 (4.60 / 4.40) | 5/5 | 18 |"),
        ],
    ),
]
TASKS_SCORE_GAP = Num("0.6", "post", "조건 간 점수 차이(0.6 이하)", "(0.6 or less)")

# (4) router, before -> now, per step
ROUTER = [  # (key, before, now, kind): kind "frac" = a/b, "pct" = share as %, "dec" = 2 decimals
    (
        "fired",
        Num("39/57", "§15", "| fired (any skillfetch call) | 39/57 (0.68) |"),
        Num("55/57", "§15", "| 39/57 (0.68) | 55/57 (0.96) |"),
        "frac",
    ),
    # drawn as "did not fire" = 30 - fired
    (
        "trivial",
        Num("0/30", "§15", "| fired (any skillfetch call) | 0/30 | 1/30 |"),
        Num("1/30", "§15", "| fired (any skillfetch call) | 0/30 | 1/30 |"),
        "not_fired",
    ),
    (
        "hit50",  # hit (i) @50, oracle v3
        Num(
            "0.891",
            "§13",
            "| R-a router rule (previous) | BM25, RRF | 0.409 | 0.737 | 0.420 | "
            "0.696 | 0.316 | 0.656 | 0.711 | 0.891 |",
        ),
        Num(
            "0.930",
            "§13",
            "| R-c router rule (shipped) | BM25, RRF | 0.457 | 0.808 | 0.467 | "
            "0.746 | 0.362 | 0.770 | 0.754 | 0.930 |",
        ),
        "pct",
    ),
    (
        "none",  # S-0 (6a) -> S-b' (B-0, shipped)
        Num("0.553", "§17", "| none-accuracy, nothing relevant (v4 85 / v3 89) | 0.553 (0.528) |"),
        Num("0.847", "§17", "none-accuracy (85) 0.847"),
        "dec",
    ),
    (
        "relevant",
        Num("0.882", "§17", "| hit (at least one relevant picked) | 0.882 (0.831) |"),
        Num("0.795", "§17", "hit (288) 0.795"),
        "dec",
    ),
]
ROUTER_POST = [  # the same before/now as the posts print them
    Num("39/57", "post", "39/57", "39/57"),
    Num("55/57", "post", "96%(55/57)", "96% (55/57)"),
    Num("89%", "post", "수정 전 89%", "89% before"),
    Num("93%", "post", "93%다(수정 전", "93% of them"),
    Num("0.55", "post", "0.55에서 0.85로", "from 0.55 to 0.85"),
    Num("0.88", "post", "0.88에서 0.80으로", "from 0.88 to 0.80"),
]


def all_numbers() -> list[Num]:
    out = [
        LICENSE_TOTAL,
        LICENSE_PERMISSIVE,
        LICENSE_PROPRIETARY,
        JUDGE_TOTAL,
        WINNER_RANGE,
        TASKS_SCORE_GAP,
        *JUDGE_SHARE.values(),
        *ROUTER_POST,
    ]
    for _, count, share in LICENSE:
        out += [count, share]
    for _, nums in JUDGE + WINNER:
        out += nums
    for _, scores, turns in TASKS:
        out += scores + turns
    for _, before, now, _ in ROUTER:
        out += [before, now]
    return out


TEXT = {
    "ko": {
        "lic_title": "스킬 {total:,}개의 라이선스 표시",
        "lic": {
            "explicit": "라이선스 명시 (permissive {p}, proprietary {q})",
            "upstream_no_license": "업스트림 레포는 찾았지만 LICENSE 파일 없음",
            "upstream_unknown": "업스트림 불명",
        },
        "judge_title": "규칙이 판정 못 한 {total:,}쌍, judge 판정",
        "judge": {
            "independent": "Independent (같은 주제, 양립)",
            "situational": "Situational (다른 상황에서 각각 맞음)",
            "conflict": "Conflict",
            "carve_out": "Carve-out (한쪽이 다른 쪽을 좁힘)",
            "error_unclear": "오류·불분명",
        },
        "pairs": "쌍",  # no space before the unit in Korean
        "winner_title": "승자를 알려준 방법별, 지정한 승자를 따른 실행 (방법마다 260회)",
        "winner": {
            "header": "스킬 앞 우선순위 헤더\n(load_skills가 넣던 문구)",
            "block": "승자를 지명하고\n충돌하는 두 줄을 인용한 블록",
            "strip": "지는 스킬의 충돌 줄을\n주석으로 치환",
        },
        "runs": "실행",
        "tasks": {
            "design": "디자인\n(랜딩 페이지)",
            "tests": "테스트 작성",
            "api": "백엔드 API",
            "docs": "문서화",
            "data": "데이터 스크립트",
        },
        "cond": ["스킬 없음", "전문가 스킬", "라우터"],
        "score_title": "점수 (1–5, 블라인드 판정)",
        "turns_title": "중앙 턴: 스킬 없음 → 라우터",
        "turns_1b": "1b 5개 태스크 전체",
        "gap_note": "점수 차 0.6 이하는 판정 간 차이보다 작다 (디자인 외 4종)",
        "tasks_foot": "디자인: 1b 재판정, 조건마다 4회. "
        "나머지: 2단계, 조건마다 5회, 두 판정의 평균. 라우터: 검색 수정 후.",
        "router_title": "라우터, 단계별 이전 → 지금",
        "router": {
            "fired": "발화 (사소하지 않은 태스크)",
            "trivial": "사소한 태스크에서 안 돎",
            "hit50": "관련 스킬이 top 50에 듦",
            "none": "맞는 게 없을 때 안 고름",
            "relevant": "관련 스킬을 하나 이상 고름",
        },
        "router_why": {
            "fired": "description 한 줄 (5단계)",
            "trivial": "description 한 줄 (5단계)",
            "hit50": "검색: 세 문장 + 요청 원문",
            "none": "선택 단계 문장 하나 (동결 후)",
            "relevant": "선택 단계 문장 하나 (동결 후)",
        },
        "before": "이전",
        "now": "지금",
        "down": "내려간 항목",
    },
    "en": {
        "lic_title": "License status of {total:,} skills",
        "lic": {
            "explicit": "License stated ({p} permissive, {q} proprietary)",
            "upstream_no_license": "Upstream repo found, no LICENSE file in it",
            "upstream_unknown": "Upstream repo unknown",
        },
        "judge_title": "Judge verdicts on the {total:,} pairs the rules could not settle",
        "judge": {
            "independent": "Independent (same topic, compatible)",
            "situational": "Situational (true in different contexts)",
            "conflict": "Conflict",
            "carve_out": "Carve-out (one narrows the other)",
            "error_unclear": "Error or unclear",
        },
        "pairs": "pairs",
        "winner_title": "Runs that followed the named winner, by method (260 runs each)",
        "winner": {
            "header": "Precedence header before the skills\n(what load_skills emitted)",
            "block": "Block naming the winner,\nquoting both conflicting lines",
            "strip": "Loser's conflicting lines\nreplaced by a comment",
        },
        "runs": "runs",
        "tasks": {
            "design": "Design\n(landing page)",
            "tests": "Test writing",
            "api": "Backend API",
            "docs": "Documentation",
            "data": "Data script",
        },
        "cond": ["No skill", "Expert's skill", "Router"],
        "score_title": "Score (1–5, judged blind)",
        "turns_title": "Median turns: no skill → router",
        "turns_1b": "all 5 stage 1b tasks",
        "gap_note": "Score gaps of 0.6 or less are smaller than the gap between judging passes "
        "(the four non-design types)",
        "tasks_foot": "Design: stage 1b rejudge, 4 runs per condition. Others: stage 2, 5 runs per "
        "condition, mean of two judging passes. Router: after the search fix.",
        "router_title": "The router, step by step: before → now",
        "router": {
            "fired": "Fired (non-trivial tasks)",
            "trivial": "Stayed off on trivial tasks",
            "hit50": "A relevant skill in the top 50",
            "none": "Picked nothing when nothing fits",
            "relevant": "Picked at least one relevant skill",
        },
        "router_why": {
            "fired": "one line of the description (stage 5)",
            "trivial": "one line of the description (stage 5)",
            "hit50": "search: three sentences + the request",
            "none": "one sentence in selection (after the freeze)",
            "relevant": "one sentence in selection (after the freeze)",
        },
        "before": "before",
        "now": "now",
        "down": "went down",
    },
}

INK, MUTED, GRID = "#222222", "#6b6b6b", "#d9d9d9"
BLUE, RED, GREEN, AMBER, GRAY = "#2f6db5", "#c0392b", "#2e8b57", "#d9a441", "#b5b5b5"
HIGHLIGHT = "#fff3c4"
FONTS = ["Noto Sans KR", "Apple SD Gothic Neo", "NanumGothic", "Nanum Gothic", "DejaVu Sans"]


def _setup():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    have = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams.update(
        {
            "font.family": [f for f in FONTS if f in have] or ["DejaVu Sans"],
            "font.size": 10,
            "axes.edgecolor": MUTED,
            "axes.labelcolor": INK,
            "xtick.color": MUTED,
            "ytick.color": INK,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    return plt


def _save(plt, fig, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return path


def _clean(ax, left=False):
    for side in ("top", "right") + (("left",) if not left else ()):
        ax.spines[side].set_visible(False)


def fig_license(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(8.5, 2.3))
    colors = [GREEN, AMBER, GRAY]
    left = 0.0
    total = val(LICENSE_TOTAL)
    for (_, count, share), color in zip(LICENSE, colors, strict=True):
        width = val(count) / total * 100
        ax.barh(0, width, left=left, color=color, edgecolor="white", height=0.6)
        ax.text(
            left + width / 2,
            0,
            f"{share.raw}\n{int(val(count)):,}",
            ha="center",
            va="center",
            color="white" if color != GRAY else INK,
            fontsize=11,
            fontweight="bold",
        )
        left += width
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    _clean(ax)
    ax.set_title(t["lic_title"].format(total=int(total)), loc="left", fontsize=12, color=INK)
    labels = [
        t["lic"][k].format(p=LICENSE_PERMISSIVE.raw, q=LICENSE_PROPRIETARY.raw)
        for k, _, _ in LICENSE
    ]
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    ax.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.32),
        ncol=1,
        frameon=False,
        fontsize=9.5,
    )
    return _save(plt, fig, f"fig1-licenses-{lang}.png")


def fig_conflicts(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(8.5, 6.2), gridspec_kw={"height_ratios": [5, 3.4], "hspace": 0.4}
    )
    keys = [k for k, _ in JUDGE]
    counts = [sum(int(val(n)) for n in nums) for _, nums in JUDGE]
    total = int(val(JUDGE_TOTAL))
    ys = range(len(keys))[::-1]
    colors = [GRAY, GRAY, RED, AMBER, GRAY]
    top.barh(list(ys), counts, color=colors, height=0.62)
    for y, c, k in zip(ys, counts, keys, strict=True):
        sep = "" if lang == "ko" else " "
        top.text(
            c + total * 0.01,
            y,
            f"{c:,}{sep}{t['pairs']} ({JUDGE_SHARE[k].raw})",
            va="center",
            fontsize=9.5,
            color=INK,
        )
    top.set_yticks(list(ys), [t["judge"][k] for k in keys])
    top.set_xlim(0, total)
    top.xaxis.set_visible(False)
    _clean(top, left=True)
    top.set_title(t["judge_title"].format(total=total), loc="left", fontsize=12, color=INK)

    mkeys = [k for k, _ in WINNER]
    shares = []
    labels = []
    for _, nums in WINNER:
        a = sum(frac(n)[0] for n in nums)
        b = sum(frac(n)[1] for n in nums)
        shares.append(a / b * 100)
        labels.append(f"{a / b * 100:.0f}% ({a}/{b})")
    ys = range(len(mkeys))[::-1]
    bottom.barh(list(ys), shares, color=BLUE, height=0.6)
    for y, s, label in zip(ys, shares, labels, strict=True):
        bottom.text(
            s + 1,
            y,
            label,
            va="center",
            fontsize=9.5,
            color=INK,
            zorder=3,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 1},
        )
    bottom.axvline(50, color=INK, linestyle="--", linewidth=1)
    bottom.set_xlim(0, 100)
    bottom.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    bottom.set_yticks(list(ys), [t["winner"][k] for k in mkeys])
    _clean(bottom, left=True)
    bottom.set_title(t["winner_title"], loc="left", fontsize=12, color=INK)
    return _save(plt, fig, f"fig2-conflicts-{lang}.png")


def fig_tasks(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, (ax, tx) = plt.subplots(
        1, 2, figsize=(10, 5.4), sharey=True, gridspec_kw={"width_ratios": [3, 2], "wspace": 0.08}
    )
    n = len(TASKS)
    centers = [n - 1 - i for i in range(n)]
    h = 0.25
    colors = [GRAY, GREEN, BLUE]
    for i, (key, scores, _) in enumerate(TASKS):
        y = centers[i]
        if key == "design":
            for a in (ax, tx):
                a.axhspan(y - 0.48, y + 0.48, color=HIGHLIGHT, zorder=0)
        for j, (s, c) in enumerate(zip(scores, colors, strict=True)):
            yy = y + (1 - j) * h
            ax.barh(
                yy,
                val(s) - 1,
                left=1,
                height=h * 0.9,
                color=c,
                zorder=2,
                label=t["cond"][j] if i == 0 else None,
            )
            ax.text(val(s) + 0.04, yy, s.raw, va="center", fontsize=8.5, color=INK)
    ax.set_xlim(1, 5.45)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_yticks(centers, [t["tasks"][k] for k, _, _ in TASKS])
    ax.set_ylim(-0.6, n - 0.4)
    _clean(ax, left=True)
    ax.set_title(t["score_title"], loc="left", fontsize=11.5, color=INK, pad=4)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.06), ncol=3, frameon=False)

    for i, (key, _, turns) in enumerate(TASKS):
        y = centers[i]
        a, c = val(turns[0]), val(turns[1])
        tx.plot([a, c], [y, y], color=GRID, linewidth=3, zorder=1)
        tx.scatter([a], [y], color=GRAY, s=45, zorder=3)
        tx.scatter([c], [y], color=BLUE, s=45, zorder=3)
        label = f"{turns[0].raw} → {turns[1].raw}"
        if key == "design":
            label += f"\n({t['turns_1b']})"
        tx.text(c + 1.0, y, label, va="center", fontsize=9, color=INK)
    tx.set_xlim(0, 46)
    tx.set_xticks([0, 10, 20, 30])
    tx.tick_params(axis="y", length=0)
    _clean(tx)
    tx.set_title(t["turns_title"], loc="left", fontsize=11.5, color=INK, pad=4)

    fig.text(0.125, -0.02, t["gap_note"], fontsize=10, color=INK, fontweight="bold")
    fig.text(0.125, -0.06, t["tasks_foot"], fontsize=8.5, color=MUTED)
    return _save(plt, fig, f"fig3-task-types-{lang}.png")


def _router_point(before: Num, now: Num, kind: str) -> tuple[float, float, str]:
    if kind == "frac":
        (a, b), (c, d) = frac(before), frac(now)
        return a / b, c / d, f"{before.raw} → {now.raw}"
    if kind == "not_fired":
        (a, b), (c, d) = frac(before), frac(now)
        return (b - a) / b, (d - c) / d, f"{b - a}/{b} → {d - c}/{d}"
    x, y = val(before), val(now)
    if kind == "pct":
        return x, y, f"{x * 100:.0f}% → {y * 100:.0f}%"
    return x, y, f"{x:.2f} → {y:.2f}"


def fig_router(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    n = len(ROUTER)
    for i, (key, before, now, kind) in enumerate(ROUTER):
        y = n - 1 - i
        x0, x1, label = _router_point(before, now, kind)
        color = RED if x1 < x0 else BLUE
        ax.annotate(
            "",
            xy=(x1, y),
            xytext=(x0, y),
            arrowprops={"arrowstyle": "-|>", "color": color, "lw": 2, "shrinkA": 5, "shrinkB": 5},
        )
        ax.scatter([x0], [y], color=GRAY, s=60, zorder=3)
        ax.scatter([x1], [y], color=color, s=60, zorder=3)
        ax.text(
            1.035,
            y + 0.1,
            label,
            va="center",
            fontsize=10.5,
            color=color,
            fontweight="bold",
            transform=ax.get_yaxis_transform(),
        )
        ax.text(
            1.035,
            y - 0.22,
            t["router_why"][key],
            va="center",
            fontsize=8,
            color=MUTED,
            transform=ax.get_yaxis_transform(),
        )
    ax.set_yticks(range(n)[::-1], [t["router"][k] for k, *_ in ROUTER])
    ax.set_xlim(0.5, 1.0)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0], ["50%", "60%", "70%", "80%", "90%", "100%"])
    ax.set_ylim(-0.6, n - 0.4)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    _clean(ax, left=True)
    ax.set_title(t["router_title"], loc="left", fontsize=12, color=INK)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=GRAY, label=t["before"]),
        plt.Line2D([], [], marker="o", linestyle="", color=BLUE, label=t["now"]),
        plt.Line2D([], [], marker="o", linestyle="", color=RED, label=t["down"]),
    ]
    ax.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False
    )
    return _save(plt, fig, f"fig4-router-{lang}.png")


def main() -> None:
    plt = _setup()
    for lang in LANGS:
        for draw in (fig_license, fig_conflicts, fig_tasks, fig_router):
            print(draw(plt, lang).relative_to(ROOT))


if __name__ == "__main__":
    main()
