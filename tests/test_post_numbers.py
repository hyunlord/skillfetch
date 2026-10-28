"""Every number in the prose of the current posts (docs/writeup/post-{en,ko}.md) is in numbers.md.

The prose is the post without code (fenced and inline), images (their captions are checked by
test_post_figures.py), link targets, URLs, section numbers, "§" references and dates. A number
counts as found when numbers.md has it as a whole number, with or without thousands commas. A
value the posts derive (a share rounded from a fraction) is listed in DERIVED with the fraction
numbers.md holds, and the test recomputes it."""

import re
from pathlib import Path

import pytest

WRITEUP = Path(__file__).resolve().parent.parent / "docs" / "writeup"
NUMBERS = (WRITEUP / "numbers.md").read_text()
POSTS = {lang: (WRITEUP / f"post-{lang}.md").read_text() for lang in ("en", "ko")}

# value in a post -> (fraction in numbers.md, how the post rounds it)
DERIVED = {
    # §8-§10: the named skill followed in 145/260 runs, printed beside the fraction
    "56%": ("145/260", lambda a, b: f"{a / b * 100:.0f}%"),
}


def prose(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"^#+ \d+\.", "#", text, flags=re.M)
    text = re.sub(r"§\s?\d+(?:[–-]§?\d+)?", " ", text)
    return re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", text)


def numbers_in(text: str) -> set[str]:
    return {x.rstrip(",.") for x in re.findall(r"\$?\d[\d,]*(?:\.\d+)?%?", prose(text))}


def in_numbers_md(token: str) -> bool:
    for form in {token, token.replace(",", "")}:
        if re.search(r"(?<![\d.,])" + re.escape(form) + r"(?![\d]|[.,]\d)", NUMBERS):
            return True
    return False


@pytest.mark.parametrize("lang", sorted(POSTS))
def test_every_number_in_the_post_is_in_numbers_md(lang):
    missing = sorted(
        t for t in numbers_in(POSTS[lang]) if not in_numbers_md(t) and t not in DERIVED
    )
    assert not missing, f"post-{lang}.md has numbers numbers.md does not: {missing}"


@pytest.mark.parametrize("value", sorted(DERIVED))
def test_derived_values_follow_from_numbers_md(value):
    fraction, rounding = DERIVED[value]
    assert fraction in NUMBERS
    a, b = map(int, fraction.split("/"))
    assert rounding(a, b) == value
    assert all(value in post for post in POSTS.values())


def test_the_check_would_catch_a_number_that_is_not_in_numbers_md():
    assert not in_numbers_md("987,654,321")
    assert numbers_in("caught 38–40 of 40, $0.02 a call, see §31 and `rm -rf ~`") == {
        "38",
        "40",
        "$0.02",
    }
