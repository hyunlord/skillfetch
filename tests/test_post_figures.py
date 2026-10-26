"""Every number in the post figures (scripts/make_post_figures.py) is in the source it cites:
a numbers.md section, or both posts."""

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


def _section(n: str) -> str:
    match = re.search(rf"^## {n}\. .*?(?=^## \d+\. |\Z)", NUMBERS, re.M | re.S)
    assert match, f"numbers.md has no section {n}"
    return match.group(0)


@pytest.mark.parametrize("num", FIGURES.all_numbers(), ids=lambda n: f"{n.src}:{n.raw}")
def test_figure_number_is_in_its_source(num):
    assert num.raw in num.where
    if num.src == "post":
        assert num.raw in num.where_en
        assert num.where in POSTS["ko"]
        assert num.where_en in POSTS["en"]
    else:
        assert num.src.startswith("§")
        assert num.where in _section(num.src[1:])


def test_derived_values_match_the_posts():
    # shares drawn in figure 2 (bottom) are the ones the posts print
    for (_, nums), expect in zip(FIGURES.WINNER, ("43%", "56%", "46%"), strict=True):
        a = sum(FIGURES.frac(n)[0] for n in nums)
        b = sum(FIGURES.frac(n)[1] for n in nums)
        assert f"{a / b * 100:.0f}%" == expect
        for post in POSTS.values():
            assert f"{expect} ({a}/{b})" in post
    # error + unclear, drawn as one bar
    assert sum(int(FIGURES.val(n)) for n in FIGURES.JUDGE[-1][1]) == 7
