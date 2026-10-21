"""profile_repo reads manifest files only (CLAUDE.md tool surface)."""

import json

from skillfetch.index.profile import profile_repo


def test_javascript_repo(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19", "next": "15"},
                "devDependencies": {"typescript": "5", "vitest": "3"},
            }
        )
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
    (tmp_path / "tailwind.config.ts").write_text("export default {}\n")
    p = profile_repo(tmp_path)
    assert p["languages"] == ["javascript", "typescript"]
    assert p["frameworks"] == ["nextjs", "react", "tailwind", "vitest"]
    assert p["package_managers"] == ["pnpm"]
    assert set(p["tags"]) == {*p["languages"], *p["frameworks"], *p["package_managers"]}


def test_python_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\ndependencies = ["Django>=5", "pydantic"]\n'
        '[dependency-groups]\ndev = ["pytest>=8"]\n'
    )
    (tmp_path / "uv.lock").write_text("version = 1\n")
    p = profile_repo(tmp_path)
    assert p["languages"] == ["python"]
    assert p["frameworks"] == ["django", "pydantic", "pytest"]
    assert p["package_managers"] == ["uv"]


def test_go_and_rust(tmp_path):
    (tmp_path / "go.mod").write_text("module x\n\nrequire github.com/gin-gonic/gin v1.10.0\n")
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "x"\n[dependencies]\ntokio = "1"\n')
    p = profile_repo(tmp_path)
    assert p["languages"] == ["go", "rust"]
    assert p["frameworks"] == ["gin", "tokio"]


def test_source_files_are_never_read(tmp_path):
    (tmp_path / "app.py").write_text("import django\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "package.json").write_text('{"dependencies": {"react": "1"}}')
    p = profile_repo(tmp_path)
    assert p["languages"] == [] and p["frameworks"] == [] and p["manifests"] == []


def test_broken_manifests_do_not_raise(tmp_path):
    (tmp_path / "package.json").write_text("{not json")
    (tmp_path / "pyproject.toml").write_text("[broken")
    p = profile_repo(tmp_path)
    assert p["languages"] == ["javascript", "python"]


def test_not_a_directory(tmp_path):
    assert profile_repo(tmp_path / "nope")["error"] == "not a directory"


def test_session_caches_profiles(tmp_path):
    from indexkit import make_index

    from skillfetch.index.loader import Index
    from skillfetch.mcp.session import Session

    s = Session(Index.load(make_index(tmp_path / "i")))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "go.mod").write_text("module x\n")
    first = s.profile_repo(str(repo))
    (repo / "Cargo.toml").write_text('[package]\nname = "x"\n')
    assert s.profile_repo(str(repo)) is first  # cached for the session
