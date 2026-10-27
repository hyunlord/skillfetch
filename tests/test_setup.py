"""`skillfetch setup` in a temporary home: no network, no real `claude` CLI, and the real
user settings are never read or written."""

import json
import subprocess
from pathlib import Path

import pytest

from skillfetch import cli
from skillfetch import setup as setup_mod
from skillfetch.setup import AUTO_NOTE, SKILLS, Setup, asset_skill, main

ROOT = Path(__file__).resolve().parent.parent


class Recorder:
    def __init__(self, code=0):
        self.calls, self.code = [], code

    def __call__(self, cmd):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.code, "", "boom" if self.code else "")


def _setup(tmp_path, **kw):
    out, runner, synced = [], kw.pop("runner", None) or Recorder(), []
    s = Setup(
        home=tmp_path / "home",
        cwd=tmp_path / "repo",
        run=runner,
        which=kw.pop("which", lambda name: "/usr/bin/claude"),
        do_sync=lambda dest: synced.append(dest) or f"index installed: {dest}",
        out=out.append,
        **kw,
    )
    return s, out, runner, synced


def test_setup_shows_the_plan_then_installs(tmp_path):
    s, out, runner, synced = _setup(tmp_path)
    assert main(s, remove=False, yes=False, ask=lambda q: "y") == 0
    plan = out[0]
    assert "~/.claude/skills/skillfetch-vet/SKILL.md" in plan
    assert "Claude Code writes it to ~/.claude.json" in plan
    assert "serve --vet" in plan and "auto-apply (per-task routing) = off" in plan
    vet = tmp_path / "home" / ".claude" / "skills" / "skillfetch-vet" / "SKILL.md"
    assert vet.read_text() == asset_skill("vet")
    assert not (vet.parents[1] / SKILLS["router"]).exists()
    assert runner.calls == [
        [
            "claude",
            "mcp",
            "add",
            "-s",
            "user",
            "skillfetch",
            "--",
            "uvx",
            "--from",
            setup_mod.DEFAULT_FROM,
            "skillfetch",
            "serve",
            "--vet",
        ]
    ]
    assert synced == [tmp_path / "home" / ".skillfetch" / "index"]


def test_declining_changes_nothing(tmp_path):
    s, out, runner, synced = _setup(tmp_path)
    assert main(s, remove=False, yes=False, ask=lambda q: "n") == 1
    assert out[-1] == "Nothing changed."
    assert not (tmp_path / "home").exists() and runner.calls == [] and synced == []


def test_auto_adds_the_router_and_says_what_it_costs(tmp_path):
    s, out, runner, _ = _setup(tmp_path, auto=True)
    assert main(s, remove=False, yes=True) == 0
    assert AUTO_NOTE in out[0] and "numbers.md §26" in AUTO_NOTE and "+62%" in AUTO_NOTE
    assert "§28" in AUTO_NOTE and "not better than no skill" in AUTO_NOTE
    skills = tmp_path / "home" / ".claude" / "skills"
    assert (skills / "skillfetch-router" / "SKILL.md").read_text() == asset_skill("router")
    assert runner.calls[0][-2:] == ["skillfetch", "serve"]  # routing tools too, no --vet


def test_project_scope(tmp_path):
    s, out, runner, _ = _setup(tmp_path, scope="project", sync=False)
    assert main(s, remove=False, yes=True) == 0
    assert (tmp_path / "repo" / ".claude" / "skills" / "skillfetch-vet" / "SKILL.md").is_file()
    assert runner.calls[0][3:5] == ["-s", "project"]
    assert str(tmp_path / "repo" / ".mcp.json") in out[0]


def test_existing_files_and_entries_are_shown_not_overwritten(tmp_path):
    s, out, runner, _ = _setup(tmp_path, sync=False)
    vet = s.skills_root / "skillfetch-vet" / "SKILL.md"
    vet.parent.mkdir(parents=True)
    vet.write_text("my own version\n")
    config = tmp_path / "home" / ".claude.json"
    config.write_text(json.dumps({"mcpServers": {"skillfetch": {"command": "skillfetch"}}}))
    assert main(s, remove=False, yes=True) == 0
    plan = out[0]
    assert "differs; left as it is" in plan and "-my own version" in plan
    assert "a different entry exists in ~/.claude.json" in plan and '+  "command": "uvx"' in plan
    assert out[-1] == "\nNothing to change."
    assert vet.read_text() == "my own version\n" and runner.calls == []


def test_rerun_is_unchanged(tmp_path):
    s, out, runner, _ = _setup(tmp_path, sync=False)
    main(s, remove=False, yes=True)
    entry = s.server_entry()
    (tmp_path / "home" / ".claude.json").write_text(
        json.dumps({"mcpServers": {"skillfetch": entry}})
    )
    out.clear()
    assert main(s, remove=False, yes=True) == 0
    assert "already registered, unchanged" in out[0] and "already installed, unchanged" in out[0]


def test_remove_undoes_only_what_setup_installed(tmp_path):
    s, out, runner, _ = _setup(tmp_path, auto=True, sync=False)
    main(s, remove=False, yes=True)
    (tmp_path / "home" / ".claude.json").write_text(
        json.dumps({"mcpServers": {"skillfetch": s.server_entry()}})
    )
    router = s.skills_root / "skillfetch-router" / "SKILL.md"
    router.write_text(router.read_text() + "edited\n")
    out.clear()
    runner.calls.clear()
    assert main(s, remove=True, yes=True) == 0
    assert not (s.skills_root / "skillfetch-vet").exists()
    assert router.is_file() and "changed since setup; left as it is" in out[0]
    assert runner.calls == [["claude", "mcp", "remove", "-s", "user", "skillfetch"]]
    assert "index at ~/.skillfetch/index is kept" in out[0]


def test_without_the_claude_cli_the_command_is_printed(tmp_path):
    s, out, runner, _ = _setup(tmp_path, sync=False, which=lambda name: None)
    assert main(s, remove=False, yes=True) == 1
    assert any("not on PATH" in line and "claude mcp add" in line for line in out)
    assert runner.calls == []


def test_cli_passes_the_options(monkeypatch):
    seen = {}

    def fake_main(setup, remove, yes):
        seen.update(setup=setup, remove=remove, yes=yes)
        return 0

    monkeypatch.setattr(setup_mod, "main", fake_main)
    assert cli.main(["setup", "--project", "--auto", "--no-sync", "-y"]) == 0
    s = seen["setup"]
    assert (s.scope, s.auto, s.sync, seen["yes"], seen["remove"]) == (
        "project",
        True,
        False,
        True,
        False,
    )
    assert cli.main(["setup", "--remove"]) == 0 and seen["remove"] and seen["setup"].scope == "user"
    with pytest.raises(SystemExit):
        cli.main(["setup", "--user", "--project"])


def test_packaged_skills_are_the_assets():
    for kind, folder in (("vet", "vet-skill"), ("router", "router-skill")):
        assert asset_skill(kind) == (ROOT / "assets" / folder / "SKILL.md").read_text()
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert '"assets/vet-skill/SKILL.md" = "skillfetch/_assets/vet-skill/SKILL.md"' in pyproject


# --- other clients (Codex, Cursor), from each client's documentation ---------------------


def test_codex_appends_a_table_and_installs_skills_under_agents(tmp_path):
    import tomllib

    s, out, runner, _ = _setup(tmp_path, client="codex", sync=False)
    config = tmp_path / "home" / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    config.write_text('model = "gpt-6-astra"\n\n[mcp_servers.other]\ncommand = "other"\n')
    assert main(s, remove=False, yes=True) == 0
    assert "append to ~/.codex/config.toml" in out[0] and "[mcp_servers.skillfetch]" in out[0]
    data = tomllib.loads(config.read_text())
    assert data["model"] == "gpt-6-astra" and data["mcp_servers"]["other"]["command"] == "other"
    assert data["mcp_servers"]["skillfetch"] == {
        "command": "uvx",
        "args": ["--from", setup_mod.DEFAULT_FROM, "skillfetch", "serve", "--vet"],
    }
    vet = tmp_path / "home" / ".agents" / "skills" / "skillfetch-vet" / "SKILL.md"
    assert vet.read_text() == asset_skill("vet") and runner.calls == []
    out.clear()
    assert main(s, remove=False, yes=True) == 0
    assert "already registered, unchanged" in out[0]
    out.clear()
    assert main(s, remove=True, yes=True) == 0
    data = tomllib.loads(config.read_text())
    assert "skillfetch" not in data["mcp_servers"] and data["mcp_servers"]["other"]
    assert config.read_text().startswith('model = "gpt-6-astra"') and not vet.exists()


def test_codex_project_scope_and_unparsable_config(tmp_path):
    s, out, _, _ = _setup(tmp_path, client="codex", scope="project", sync=False)
    assert main(s, remove=False, yes=True) == 0
    assert (tmp_path / "repo" / ".codex" / "config.toml").is_file()
    assert (tmp_path / "repo" / ".agents" / "skills" / "skillfetch-vet" / "SKILL.md").is_file()
    assert "trusted projects only" in out[0]
    broken = tmp_path / "home2" / ".codex" / "config.toml"
    broken.parent.mkdir(parents=True)
    broken.write_text("this is = = not toml\n")
    s2, out2, _, _ = _setup(tmp_path, client="codex", sync=False)
    s2.home = tmp_path / "home2"
    main(s2, remove=False, yes=True)
    assert "cannot be parsed; left as it is" in out2[0]
    assert broken.read_text() == "this is = = not toml\n"


def test_codex_edited_table_is_left_on_remove(tmp_path):
    s, out, _, _ = _setup(tmp_path, client="codex", sync=False)
    main(s, remove=False, yes=True)
    config = tmp_path / "home" / ".codex" / "config.toml"
    config.write_text(config.read_text().replace("args = [", "startup_timeout_sec = 20\nargs = ["))
    out.clear()
    main(s, remove=True, yes=True)
    assert "edited after setup; left as it is" in out[0]
    assert "[mcp_servers.skillfetch]" in config.read_text()


def test_cursor_merges_into_mcp_json_and_installs_no_skill(tmp_path):
    s, out, runner, _ = _setup(tmp_path, client="cursor", sync=False)
    config = tmp_path / "home" / ".cursor" / "mcp.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"mcpServers": {"other": {"command": "other"}}}))
    assert main(s, remove=False, yes=True) == 0
    assert "add to `mcpServers` in ~/.cursor/mcp.json" in out[0]
    assert "skills: none for Cursor" in out[0]
    servers = json.loads(config.read_text())["mcpServers"]
    assert servers["other"] == {"command": "other"}
    assert servers["skillfetch"]["args"][-2:] == ["serve", "--vet"]
    assert not (tmp_path / "home" / ".claude").exists() and runner.calls == []
    out.clear()
    assert main(s, remove=True, yes=True) == 0
    assert json.loads(config.read_text())["mcpServers"] == {"other": {"command": "other"}}


def test_cursor_different_entry_is_shown_not_overwritten(tmp_path):
    s, out, _, _ = _setup(tmp_path, client="cursor", scope="project", sync=False)
    config = tmp_path / "repo" / ".cursor" / "mcp.json"
    config.parent.mkdir(parents=True)
    mine = {"mcpServers": {"skillfetch": {"command": "skillfetch", "args": ["serve"]}}}
    config.write_text(json.dumps(mine))
    assert main(s, remove=False, yes=True) == 0
    assert "a different entry exists in" in out[0] and out[-1] == "\nNothing to change."
    assert json.loads(config.read_text()) == mine


def test_cli_client_option(monkeypatch):
    seen = {}
    monkeypatch.setattr(setup_mod, "main", lambda setup, remove, yes: seen.update(s=setup) or 0)
    assert cli.main(["setup", "--client", "codex", "--no-sync", "-y"]) == 0
    assert seen["s"].client == "codex"
    with pytest.raises(SystemExit):
        cli.main(["setup", "--client", "vim"])
