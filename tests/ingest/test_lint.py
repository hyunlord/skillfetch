"""Static lint (index-format.md §1.3)."""

from conftest import write_skill

from skillfetch.ingest.lint import lint_skill


def rules(result, kind="errors"):
    return [(i.rule, i.line_no) for i in getattr(result, kind)]


def test_valid_skill_passes(tmp_path):
    result = lint_skill(write_skill(tmp_path, "ok"))
    assert result.ok and result.errors == [] and result.warnings == []


def test_missing_skill_md(tmp_path):
    (tmp_path / "empty").mkdir()
    assert rules(lint_skill(tmp_path / "empty")) == [("lint.missing-skill-md", None)]


def test_missing_frontmatter(tmp_path):
    result = lint_skill(write_skill(tmp_path, "x", frontmatter="\n"))
    assert not result.ok
    assert rules(result) == [("lint.frontmatter-missing", 1)]


def test_unclosed_frontmatter(tmp_path):
    result = lint_skill(write_skill(tmp_path, "x", frontmatter="---\nname: x\n"))
    assert rules(result) == [("lint.frontmatter-unclosed", 1)]


def test_invalid_yaml_frontmatter(tmp_path):
    fm = "---\nname: x\ndescription: Atomic commits: one change\n---\n"
    assert rules(lint_skill(write_skill(tmp_path, "x", frontmatter=fm))) == [
        ("lint.frontmatter-invalid", 3)
    ]


def test_frontmatter_must_be_a_mapping(tmp_path):
    fm = "---\n- just\n- a list\n---\n"
    assert rules(lint_skill(write_skill(tmp_path, "x", frontmatter=fm))) == [
        ("lint.frontmatter-invalid", 1)
    ]


def test_name_and_description_required(tmp_path):
    fm = "---\nname: x\ndescription: '   '\n---\n"
    assert rules(lint_skill(write_skill(tmp_path, "a", frontmatter=fm))) == [
        ("lint.missing-description", 1)
    ]
    fm = "---\ndescription: hello\n---\n"
    assert rules(lint_skill(write_skill(tmp_path, "b", frontmatter=fm))) == [
        ("lint.missing-name", 1)
    ]


def test_long_body_is_a_warning_not_an_error(tmp_path):
    ok = lint_skill(write_skill(tmp_path, "a", "line\n" * 500))
    assert ok.warnings == []
    long = lint_skill(write_skill(tmp_path, "b", "line\n" * 501))
    assert long.ok
    assert [w.rule for w in long.warnings] == ["lint.body-too-long"]


def test_token_estimate_warning(tmp_path):
    result = lint_skill(write_skill(tmp_path, "a", "word " * 4100 + "\n"))
    assert result.ok
    assert [w.rule for w in result.warnings] == ["lint.body-too-many-tokens"]


def test_broken_relative_link_is_an_error(tmp_path):
    body = "# T\n\nSee [the guide](references/guide.md) and [missing](references/nope.md).\n"
    d = write_skill(tmp_path, "a", body, files={"references/guide.md": "ok"})
    result = lint_skill(d)
    assert rules(result) == [("lint.broken-link", 7)]
    assert "references/nope.md" in result.errors[0].message


def test_link_forms_that_resolve(tmp_path):
    body = (
        "![diagram](img/flow%20chart.png)\n"
        "[section](guide.md#setup) and [query](guide.md?plain=1)\n"
        "[ref]: guide.md\n"
        '[titled](guide.md "Guide")\n'
        "[angle](<img/flow chart.png>)\n"
    )
    d = write_skill(tmp_path, "a", body, files={"guide.md": "g", "img/flow chart.png": "p"})
    assert lint_skill(d).ok


def test_links_that_are_not_checked(tmp_path):
    body = (
        "[web](https://example.com/x.md) [mail](mailto:a@b.c) [top](#rules)\n"
        "Inline `[code](nope.md)` is not a link.\n"
        "```\n[fenced](nope.md)\n```\n"
        "~~~md\n[tilde](nope.md)\n~~~\n"
    )
    assert lint_skill(write_skill(tmp_path, "a", body)).ok


def test_reference_definition_is_checked(tmp_path):
    assert rules(lint_skill(write_skill(tmp_path, "a", "[ref]: refs/missing.md\n"))) == [
        ("lint.broken-link", 5)
    ]


def test_link_outside_the_skill_folder_is_an_error(tmp_path):
    write_skill(tmp_path, "other")
    d = write_skill(tmp_path, "a", "See [other](../other/SKILL.md).\n")
    assert rules(lint_skill(d)) == [("lint.link-outside-skill", 5)]


def test_absolute_path_link_is_an_error(tmp_path):
    assert rules(lint_skill(write_skill(tmp_path, "a", "[abs](/etc/hosts)\n"))) == [
        ("lint.link-outside-skill", 5)
    ]


def test_fixture_corpus_lints_clean():
    from conftest import fixture_skill_dirs

    for d in fixture_skill_dirs():
        result = lint_skill(d)
        assert result.ok and result.warnings == [], (d.name, result)
