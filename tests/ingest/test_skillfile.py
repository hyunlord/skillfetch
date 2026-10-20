"""Reading, discovering and hashing skill folders (index-format.md §1.2)."""

from conftest import write_skill

from skillfetch.ingest.skillfile import content_hash, discover_skills, read_skill


def test_read_skill_splits_frontmatter_and_body(tmp_path):
    d = write_skill(tmp_path, "demo", "# Demo\n\nBody line.\n")
    doc = read_skill(d)
    assert doc.frontmatter == {"name": "demo", "description": "A test skill."}
    assert doc.frontmatter_error is None
    assert doc.body_start == 5
    assert doc.lines[doc.body_start - 1] == "# Demo"
    assert doc.body_lines == ["# Demo", "", "Body line."]


def test_read_skill_strips_bom_and_crlf(tmp_path):
    d = tmp_path / "bom"
    d.mkdir()
    raw = "\ufeff---\r\nname: bom\r\ndescription: x\r\n---\r\nhi\r\n"
    (d / "SKILL.md").write_bytes(raw.encode())
    doc = read_skill(d)
    assert doc.frontmatter == {"name": "bom", "description": "x"}
    assert doc.body_lines == ["hi"]


def test_read_skill_reports_yaml_error_line(tmp_path):
    d = write_skill(tmp_path, "bad", frontmatter="---\nname: bad\ndescription: a: b\n---\n")
    doc = read_skill(d)
    assert doc.frontmatter is None
    assert doc.frontmatter_error and doc.frontmatter_error_line == 3


def test_discover_finds_nested_skills_and_skips_hidden(tmp_path):
    write_skill(tmp_path, "a")
    write_skill(tmp_path / "group", "b")
    write_skill(tmp_path / ".hidden", "c")
    write_skill(tmp_path / "node_modules", "d")
    # a folder inside a skill belongs to that skill, even if it has a SKILL.md
    write_skill(tmp_path / "a" / "references", "nested")
    assert [p.relative_to(tmp_path).as_posix() for p in discover_skills(tmp_path)] == [
        "a",
        "group/b",
    ]


def test_discover_accepts_a_single_skill_dir(tmp_path):
    d = write_skill(tmp_path, "solo")
    assert discover_skills(d) == [d]


def test_content_hash_ignores_formatting_noise_and_sidecar(tmp_path):
    a = write_skill(tmp_path, "a", "# T\n\nline\n", files={"ref.md": "x"})
    b = tmp_path / "b"
    b.mkdir()
    (b / "SKILL.md").write_text(
        "---\r\nname: a\r\ndescription: A test skill.\r\n---\r\n# T  \r\n\r\nline\r\n\r\n"
    )
    (b / "ref.md").write_text("x")
    (b / "constraints.json").write_text("{}")
    (b / ".DS_Store").write_text("junk")
    assert content_hash(a) == content_hash(b)
    assert len(content_hash(a)) == 64


def test_content_hash_covers_other_files(tmp_path):
    a = write_skill(tmp_path, "a", files={"ref.md": "x"})
    b = write_skill(tmp_path, "b", files={"ref.md": "y"})
    c = write_skill(tmp_path, "c", files={"other.md": "x"})
    (b / "SKILL.md").write_text((a / "SKILL.md").read_text())
    (c / "SKILL.md").write_text((a / "SKILL.md").read_text())
    assert len({content_hash(a), content_hash(b), content_hash(c)}) == 3
