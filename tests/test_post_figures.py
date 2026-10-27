"""Every number in the post figures (scripts/make_post_figures.py) is in the source it cites:
a numbers.md section, or both posts of a date (figures 1–4: the 2026-10-22 posts)."""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WRITEUP = ROOT / "docs" / "writeup"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "make_post_figures", ROOT / "scripts" / "make_post_figures.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIGURES = _load_script()
NUMBERS = (WRITEUP / "numbers.md").read_text()
POSTS = {lang: (WRITEUP / f"post-{lang}.md").read_text() for lang in ("ko", "en")}
OLD_POSTS = {lang: (WRITEUP / f"post-2026-10-22-{lang}.md").read_text() for lang in ("ko", "en")}


def _section(n: str) -> str:
    match = re.search(rf"^## {n}\. .*?(?=^## \d+\. |\Z)", NUMBERS, re.M | re.S)
    assert match, f"numbers.md has no section {n}"
    return match.group(0)


@pytest.mark.parametrize("num", FIGURES.all_numbers(), ids=lambda n: f"{n.src}:{n.raw}")
def test_figure_number_is_in_its_source(num):
    assert num.raw in num.where
    if num.src == "post-2026-10-22":
        assert num.raw in num.where_en
        assert num.where in OLD_POSTS["ko"]
        assert num.where_en in OLD_POSTS["en"]
    else:
        assert num.src.startswith("§")
        assert num.where in _section(num.src[1:])


def test_derived_values_match_the_posts():
    # shares drawn in figure 2 (bottom) are the ones the posts print
    for (_, nums), expect in zip(FIGURES.WINNER, ("43%", "56%", "46%"), strict=True):
        a = sum(FIGURES.frac(n)[0] for n in nums)
        b = sum(FIGURES.frac(n)[1] for n in nums)
        assert f"{a / b * 100:.0f}%" == expect
        for post in OLD_POSTS.values():
            assert f"{expect} ({a}/{b})" in post
    # error + unclear, drawn as one bar
    assert sum(int(FIGURES.val(n)) for n in FIGURES.JUDGE[-1][1]) == 7


def test_derived_values_of_the_current_figures():
    # Stage 13: R's cost over A's is the 62% numbers.md §26 states
    cost = {row[0]: FIGURES.val(row[4]) for row in FIGURES.STAGE13}
    assert f"{(cost['R'] / cost['A'] - 1) * 100:.0f}%" == FIGURES.STAGE13_COST_UP.raw
    # knowledge gap: 180 answers minus the wrong runs drawn is the 173 correct
    wrong = sum(int(n.raw.split(" of ")[0]) for _, n in FIGURES.KG_MISSED)
    assert FIGURES.val(FIGURES.KG_TOTAL) - wrong == FIGURES.val(FIGURES.KG_CORRECT)
    assert sum(FIGURES.val(n) for _, n in FIGURES.KG_OFFICIAL) == FIGURES.val(FIGURES.KG_QUESTIONS)
    # index scan: each share is its count over 2,785, and the advice adds up
    total = FIGURES.val(FIGURES.SCAN_TOTAL)
    for _, count, share in FIGURES.SCAN + FIGURES.SCAN_ADVICE:
        assert f"{FIGURES.val(count) / total * 100:.1f}%" == share.raw
    assert sum(FIGURES.val(c) for _, c, _ in FIGURES.SCAN_ADVICE) == total


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_current_posts_show_the_figures_and_their_numbers(lang):
    post = POSTS[lang]
    for name in ("fig5-stage13", "fig6-knowledge", "fig7-index-scan"):
        assert f"img/{name}-{lang}.png" in post
        assert (WRITEUP / "img" / f"{name}-{lang}.png").is_file()
    assert "img/stage13-d1-landing-p-r.png" in post
    assert (WRITEUP / "img" / "stage13-d1-landing-p-r.png").is_file()
    for _, *nums in FIGURES.STAGE13:
        for n in nums:
            assert n.raw in post
    for raw in ("173", "180", "62%", "0.246", "0.929", "0.563", "0.849", "0.905"):
        assert raw in post
    for _, _count, share in FIGURES.SCAN:
        assert share.raw in post
