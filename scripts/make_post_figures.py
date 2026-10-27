"""Draw the figures of the posts into docs/writeup/img/ as PNG (white background, 200 dpi),
Korean and English labels separately: figures 1–4 for the 2026-10-22 post
(docs/writeup/post-2026-10-22-{ko,en}.md), figures 5–7 for the current one (post-{ko,en}.md).

Every number drawn comes from the tables below. Each entry gives the number as written in its
source, the source (`§N` = docs/writeup/numbers.md section N; `post-2026-10-22` = both posts of
that date) and a line fragment that holds it; tests/test_post_figures.py checks that each
fragment is in that source. Figures do not change any number; derived values (sums, shares,
30 − fired, ratios) are computed here.

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
    src: str  # "§N" (numbers.md section) or "post-2026-10-22"
    where: str  # fragment of the source that contains raw (for a post: the Korean one)
    where_en: str = ""  # a post only: fragment of the English one


def val(n: Num) -> float:
    return float(n.raw.lstrip("$").rstrip("%").replace(",", "").split("/")[0])


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
WINNER_RANGE = Num(
    "43–56%", "post-2026-10-22", "지정한 스킬을 따른 실행은 43–56%다", "43–56% of runs"
)

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
TASKS_SCORE_GAP = Num("0.6", "post-2026-10-22", "조건 간 점수 차이(0.6 이하)", "(0.6 or less)")

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
    Num("39/57", "post-2026-10-22", "39/57", "39/57"),
    Num("55/57", "post-2026-10-22", "96%(55/57)", "96% (55/57)"),
    Num("89%", "post-2026-10-22", "수정 전 89%", "89% before"),
    Num("93%", "post-2026-10-22", "93%다(수정 전", "93% of them"),
    Num("0.55", "post-2026-10-22", "0.55에서 0.85로", "from 0.55 to 0.85"),
    Num("0.88", "post-2026-10-22", "0.88에서 0.80으로", "from 0.88 to 0.80"),
]


# (5) Stage 13: no skill (A), eight popular skills installed (P), the router (R); numbers.md §26
STAGE13 = [  # (key, mean score without d1-landing, d1-landing score, checks, cost per session)
    (
        "A",
        Num("4.618", "§26", "| mean score, without d1-landing (17) | 4.618 |"),
        Num("3.00", "§26", "R scored 4.67, A 3.00 and P 1.33"),
        Num("53/54", "§26", "| checks passed | 53/54 |"),
        Num("$0.370", "§26", "| mean API-price equivalent per session | $0.370 |"),
    ),
    (
        "P",
        Num("4.725", "§26", "| mean score, without d1-landing (17) | 4.618 | 4.725 |"),
        Num("1.33", "§26", "R scored 4.67, A 3.00 and P 1.33"),
        Num("51/54", "§26", "| checks passed | 53/54 | 51/54 |"),
        Num("$0.642", "§26", "| mean API-price equivalent per session | $0.370 | $0.642 |"),
    ),
    (
        "R",
        Num("4.627", "§26", "| mean score, without d1-landing (17) | 4.618 | 4.725 | 4.627 |"),
        Num("4.67", "§26", "R scored 4.67, A 3.00 and P 1.33"),
        Num("52/54", "§26", "| checks passed | 53/54 | 51/54 | 52/54 |"),
        Num("$0.599", "§26", "| $0.370 | $0.642 | $0.599 |"),
    ),
]
STAGE13_COST_UP = Num("62%", "§26", "R's mean cost per session was 62% higher")

# (6) knowledge gap, numbers.md §24
KG_TOTAL = Num("180", "§24", "173 of 180 answers were correct")
KG_CORRECT = Num("173", "§24", "173 of 180 answers were correct")
KG_QUESTIONS = Num("60", "§24", "2 per candidate (60)")
KG_MISSED = [  # (key, wrong runs out of 3)
    ("price", Num("3 of 3", "§24", "| Claude Opus 5.5 input price per million tokens | 3 of 3 |")),
    (
        "ios",
        Num(
            "1 of 3", "§24", "| iOS version that added AdAttributionKit conversion tags | 1 of 3 |"
        ),
    ),
    ("edpb", Num("3 of 3", "§24", "processing personal data through AI systems | 3 of 3 |")),
]
KG_OFFICIAL = [  # (key, answers)
    ("confirmed", Num("47", "§24", "confirmed 47, partial 12")),
    ("partial", Num("12", "§24", "confirmed 47, partial 12")),
    ("not_confirmed", Num("1", "§24", "not confirmed 1.")),
]

# (7) the scan rules over the released index, numbers.md §25 (all 2,785 indexed skills)
SCAN_TOTAL = Num("2,785", "§25", "| check | all indexed (n = 2,785) |")
SCAN = [  # (key, skills, share)
    (
        "scan_warning",
        Num("52", "§25", "| injection-scan warning (any) | 52 (1.9%) |"),
        Num("1.9%", "§25", "| injection-scan warning (any) | 52 (1.9%) |"),
    ),
    (
        "remote",
        Num("11", "§25", "(`network.remote-instructions`) | 11 (0.4%) |"),
        Num("0.4%", "§25", "(`network.remote-instructions`) | 11 (0.4%) |"),
    ),
    (
        "size",
        Num("67", "§25", "| size warning (any) | 67 (2.4%) |"),
        Num("2.4%", "§25", "| size warning (any) | 67 (2.4%) |"),
    ),
    (
        "scripts",
        Num("252", "§25", "| bundles scripts | 252 (9.0%) |"),
        Num("9.0%", "§25", "| bundles scripts | 252 (9.0%) |"),
    ),
    (
        "dated",
        Num("890", "§25", "| states a year or version (DATED) | 890 (32.0%) |"),
        Num("32.0%", "§25", "| states a year or version (DATED) | 890 (32.0%) |"),
    ),
    (
        "no_own_license",
        Num("2,486", "§25", "(folder LICENSE or frontmatter) | 2,486 (89.3%) |"),
        Num("89.3%", "§25", "(folder LICENSE or frontmatter) | 2,486 (89.3%) |"),
    ),
    (
        "no_license",
        Num("1,491", "§25", "| no license after the repo-root rule | 1,491 (53.5%) |"),
        Num("53.5%", "§25", "| no license after the repo-root rule | 1,491 (53.5%) |"),
    ),
]
SCAN_ADVICE = [  # (key, skills, share)
    (
        "recommended",
        Num("2,459", "§25", "| recommended | 2,459 (88.3%) |"),
        Num("88.3%", "§25", "| recommended | 2,459 (88.3%) |"),
    ),
    (
        "caution",
        Num("326", "§25", "size or scripts) | 326 (11.7%) |"),
        Num("11.7%", "§25", "size or scripts) | 326 (11.7%) |"),
    ),
    (
        "not_recommended",
        Num("0", "§25", "| not recommended | 0 (0.0%) |"),
        Num("0.0%", "§25", "| not recommended | 0 (0.0%) |"),
    ),
]
SCAN_REJECTED = Num("143", "§25", "the build rejected 143 more skills")


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
    for _, *nums in STAGE13:
        out += nums
    out += [STAGE13_COST_UP, KG_TOTAL, KG_CORRECT, KG_QUESTIONS, SCAN_TOTAL, SCAN_REJECTED]
    out += [n for _, n in KG_MISSED + KG_OFFICIAL]
    for _, count, share in SCAN + SCAN_ADVICE:
        out += [count, share]
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
        "s13_cond": {"A": "스킬 없음", "P": "인기 스킬 8개 설치", "R": "라우터"},
        "s13_score": "평균 점수, d1-landing 뺀 17개",
        "s13_d1": "d1-landing (제품 랜딩 페이지)",
        "s13_cost": "세션당 평균 비용 (API 단가 환산)",
        "s13_checks": "체크 통과 {c}",
        "s13_foot": "18개 태스크 × 3회, 블라인드 판정(Claude 2명, 1–5). "
        "P의 d1-landing 3세션은 모두 40턴 한도에서 끝났다.",
        "kg_title": "스킬 없이 답한 사실 질문 {total}개 (질문 {q}개 × 3회)",
        "kg_correct": "맞음 {n}",
        "kg_wrong": "틀림 {n}",
        "kg_missed_title": "틀린 답이 나온 질문, 3회 중 맞은 횟수",
        "kg_missed": {
            "price": "Claude Opus 5.5 입력 단가",
            "ios": "AdAttributionKit 전환 태그가\n추가된 iOS 버전",
            "edpb": "AI 시스템의 개인정보 처리에 관한\nEDPB 문서",
        },
        "kg_others": "나머지 질문 {n}개는 3회 모두 맞음",
        "kg_official_title": "정답 {q}개를 공식 문서로 대조",
        "kg_official": {"confirmed": "확인", "partial": "부분", "not_confirmed": "미확인"},
        "runs3": "{n}/3",
        "scan_title": "공개 index {total}개 스킬에 scan 규칙을 돌린 결과",
        "scan": {
            "scan_warning": "인젝션 점검 경고",
            "remote": "  그중 원격 지시",
            "size": "크기 경고",
            "scripts": "스크립트 포함",
            "dated": "연도·버전을 단정하는 줄",
            "no_own_license": "스킬 자체에 라이선스 없음",
            "no_license": "레포 루트 규칙 적용 후에도 없음",
        },
        "skills": "개",
        "advice_title": "스킬 하나씩 본 설치 권고 (라이선스는 권고에 넣지 않음)",
        "advice": {
            "recommended": "설치 권장",
            "caution": "주의",
            "not_recommended": "비권장",
        },
        "scan_foot": "index는 린트와 인젝션 점검을 통과한 스킬만 받았다. "
        "빌드에서 {n}개가 더 걸러졌다.",
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
        "s13_cond": {"A": "No skill", "P": "8 popular skills installed", "R": "Router"},
        "s13_score": "Mean score, 17 tasks without d1-landing",
        "s13_d1": "d1-landing (a product landing page)",
        "s13_cost": "Mean cost per session (API-price equivalent)",
        "s13_checks": "checks {c}",
        "s13_foot": "18 tasks × 3 runs, judged blind (two Claude judges, 1–5). "
        "All three P sessions on d1-landing ended at the 40-turn limit.",
        "kg_title": "{total} answers to factual questions without the skill "
        "({q} questions × 3 runs)",
        "kg_correct": "correct {n}",
        "kg_wrong": "wrong {n}",
        "kg_missed_title": "Questions with a wrong answer: runs answered correctly, of 3",
        "kg_missed": {
            "price": "Claude Opus 5.5 input price",
            "ios": "iOS version that added\nAdAttributionKit conversion tags",
            "edpb": "EDPB document on processing\npersonal data through AI systems",
        },
        "kg_others": "The other {n} questions: 3 of 3 correct",
        "kg_official_title": "The {q} accepted answers, checked against official sources",
        "kg_official": {
            "confirmed": "confirmed",
            "partial": "partial",
            "not_confirmed": "not confirmed",
        },
        "runs3": "{n}/3",
        "scan_title": "The scan rules over the {total} skills of the public index",
        "scan": {
            "scan_warning": "Injection-scan warning",
            "remote": "  of which remote instructions",
            "size": "Size warning",
            "scripts": "Bundles scripts",
            "dated": "States a year or version",
            "no_own_license": "No license in the skill itself",
            "no_license": "None after the repo-root rule",
        },
        "skills": "skills",
        "advice_title": "Advice per skill (the license is not part of it)",
        "advice": {
            "recommended": "recommended",
            "caution": "caution",
            "not_recommended": "not recommended",
        },
        "scan_foot": "The index admitted only skills that pass lint and the injection scan; "
        "its build rejected {n} more.",
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


def _hbar_labels(ax, ys, widths, labels, xmax):
    for y, w, label in zip(ys, widths, labels, strict=True):
        ax.text(w + xmax * 0.012, y, label, va="center", fontsize=9.5, color=INK)


def fig_stage13(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4), gridspec_kw={"wspace": 0.55})
    keys = [k for k, *_ in STAGE13]
    colors = [GRAY, AMBER, BLUE]
    ys = list(range(len(keys)))[::-1]
    panels = (
        (axes[0], 1, t["s13_score"], 5),
        (axes[1], 2, t["s13_d1"], 5),
        (axes[2], 4, t["s13_cost"], None),
    )
    for ax, col, title, top in panels:
        nums = [row[col] for row in STAGE13]
        vals = [val(n) for n in nums]
        if top:  # score: bars from 1
            ax.barh(ys, [v - 1 for v in vals], left=1, color=colors, height=0.6)
            ax.set_xlim(1, 5.6)
            ax.set_xticks([1, 2, 3, 4, 5])
            for y, n, v in zip(ys, nums, vals, strict=True):
                ax.text(v + 0.06, y, n.raw, va="center", fontsize=10, color=INK)
        else:
            xmax = max(vals) * 1.35
            ax.barh(ys, vals, color=colors, height=0.6)
            ax.set_xlim(0, xmax)
            ax.set_xticks([0, 0.2, 0.4, 0.6], ["$0", "$0.2", "$0.4", "$0.6"])
            for y, n, v in zip(ys, nums, vals, strict=True):
                ax.text(v + xmax * 0.02, y, n.raw, va="center", fontsize=10, color=INK)
        ax.set_title(title, loc="left", fontsize=10.5, color=INK)
        _clean(ax, left=True)
    axes[0].set_yticks(
        ys,
        [
            f"{t['s13_cond'][k]}\n{t['s13_checks'].format(c=row[3].raw)}"
            for k, row in zip(keys, STAGE13, strict=True)
        ],
    )
    for ax in axes[1:]:
        ax.set_yticks(ys, [""] * len(ys))
        ax.tick_params(axis="y", length=0)
    fig.text(0.125, -0.06, t["s13_foot"], fontsize=8.5, color=MUTED)
    return _save(plt, fig, f"fig5-stage13-{lang}.png")


def fig_knowledge(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, (top, mid, bottom) = plt.subplots(
        3, 1, figsize=(9, 5.6), gridspec_kw={"height_ratios": [1, 2.6, 1], "hspace": 0.9}
    )
    total, correct = int(val(KG_TOTAL)), int(val(KG_CORRECT))
    top.barh(0, correct, color=GREEN, height=0.6)
    top.barh(0, total - correct, left=correct, color=RED, height=0.6)
    top.text(
        correct / 2,
        0,
        t["kg_correct"].format(n=correct),
        ha="center",
        va="center",
        color="white",
        fontsize=10.5,
        fontweight="bold",
    )
    top.text(
        total + 2, 0, t["kg_wrong"].format(n=total - correct), va="center", fontsize=10, color=RED
    )
    top.set_xlim(0, total * 1.12)
    top.set_yticks([])
    top.xaxis.set_visible(False)
    _clean(top)
    q = int(val(KG_QUESTIONS))
    top.set_title(t["kg_title"].format(total=total, q=q), loc="left", fontsize=11.5, color=INK)

    ys = list(range(len(KG_MISSED)))[::-1]
    right = [3 - int(n.raw.split(" of ")[0]) for _, n in KG_MISSED]
    mid.barh(ys, [3] * len(ys), color=GRID, height=0.55)
    mid.barh(ys, right, color=GREEN, height=0.55)
    for y, r in zip(ys, right, strict=True):
        mid.text(
            3.06, y, t["runs3"].format(n=r), va="center", fontsize=10, color=RED if r < 3 else INK
        )
    mid.set_xlim(0, 3.5)
    mid.set_xticks([0, 1, 2, 3])
    mid.set_yticks(ys, [t["kg_missed"][k] for k, _ in KG_MISSED])
    _clean(mid, left=True)
    mid.set_title(t["kg_missed_title"], loc="left", fontsize=11, color=INK)
    mid.set_xlabel(t["kg_others"].format(n=q - len(KG_MISSED)), loc="left", fontsize=9, color=MUTED)

    left = 0
    colors = [GREEN, AMBER, GRAY]
    for (key, n), c in zip(KG_OFFICIAL, colors, strict=True):
        w = val(n)
        bottom.barh(0, w, left=left, color=c, height=0.6)
        label = f"{t['kg_official'][key]} {n.raw}"
        if w >= 8:
            bottom.text(
                left + w / 2,
                0,
                label,
                ha="center",
                va="center",
                fontsize=10,
                color="white" if c != GRAY else INK,
            )
        else:
            bottom.text(left + w + 0.8, 0, label, va="center", fontsize=9.5, color=INK)
        left += w
    bottom.set_xlim(0, q * 1.25)
    bottom.set_yticks([])
    bottom.xaxis.set_visible(False)
    _clean(bottom)
    bottom.set_title(t["kg_official_title"].format(q=q), loc="left", fontsize=11, color=INK)
    return _save(plt, fig, f"fig6-knowledge-{lang}.png")


def fig_index_scan(plt, lang: str) -> Path:
    t = TEXT[lang]
    fig, (ax, adv) = plt.subplots(
        2, 1, figsize=(9, 5.6), gridspec_kw={"height_ratios": [len(SCAN), 1.2], "hspace": 0.55}
    )
    total = val(SCAN_TOTAL)
    ys = list(range(len(SCAN)))[::-1]
    shares = [val(c) / total * 100 for _, c, _ in SCAN]
    colors = [RED, RED, AMBER, AMBER, BLUE, GRAY, GRAY]
    ax.barh(ys, shares, color=colors, height=0.62)
    sep = "" if lang == "ko" else " "
    _hbar_labels(ax, ys, shares, [f"{s.raw} ({c.raw}{sep}{t['skills']})" for _, c, s in SCAN], 100)
    ax.set_xlim(0, 118)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_yticks(ys, [t["scan"][k] for k, _, _ in SCAN])
    _clean(ax, left=True)
    ax.set_title(t["scan_title"].format(total=SCAN_TOTAL.raw), loc="left", fontsize=12, color=INK)

    left, outside = 0.0, []
    for (key, count, share), c in zip(SCAN_ADVICE, [GREEN, AMBER, RED], strict=True):
        w = val(count) / total * 100
        label = f"{t['advice'][key]} {share.raw}"
        if w:
            adv.barh(0, w, left=left, color=c, height=0.6)
        if w >= 30:
            adv.text(
                left + w / 2,
                0,
                label,
                ha="center",
                va="center",
                fontsize=10,
                color="white",
                fontweight="bold",
            )
        else:
            outside.append(label)
        left += w
    adv.text(left + 1, 0, " · ".join(outside), va="center", fontsize=9.5, color=INK)
    adv.set_xlim(0, 118)
    adv.set_yticks([])
    adv.xaxis.set_visible(False)
    _clean(adv)
    adv.set_title(t["advice_title"], loc="left", fontsize=11, color=INK)
    fig.text(0.125, 0.0, t["scan_foot"].format(n=SCAN_REJECTED.raw), fontsize=8.5, color=MUTED)
    return _save(plt, fig, f"fig7-index-scan-{lang}.png")


def main() -> None:
    plt = _setup()
    for lang in LANGS:
        for draw in (
            fig_license,
            fig_conflicts,
            fig_tasks,
            fig_router,
            fig_stage13,
            fig_knowledge,
            fig_index_scan,
        ):
            print(draw(plt, lang).relative_to(ROOT))


if __name__ == "__main__":
    main()
