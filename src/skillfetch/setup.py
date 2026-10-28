"""`skillfetch setup [--client claude-code|codex|cursor] [--auto] [--project | --user]
[--remove]`: one command for the three features (README, "Setup").

- **Check before install** (on): the vet skill (`assets/vet-skill`) and an MCP server with
  `scan_skill` and `find_skills` (`serve --vet`).
- **Find on request** (on): `find_skills`, the same server and skill.
- **Auto-apply, per-task routing** (off): `--auto` installs the router skill and serves the
  routing tools too (`serve` without `--vet`).

Where each client keeps its MCP servers and skills (from each client's documentation):
- **Claude Code:** registered with Claude Code's own `claude mcp add -s <scope>`, which writes
  `~/.claude.json` (user) or `.mcp.json` (project); skills in `~/.claude/skills/` or
  `./.claude/skills/`.
- **Codex** (learn.chatgpt.com/docs/extend/mcp, /docs/build-skills): a `[mcp_servers.<name>]`
  table with `command` and `args` in `~/.codex/config.toml` (user) or `.codex/config.toml`
  (project; Codex reads it for trusted projects only); skills in `~/.agents/skills/` (user) or
  `./.agents/skills/` (repository).
- **Cursor** (cursor.com/docs/mcp): `mcpServers.<name>` with `command` and `args` in
  `~/.cursor/mcp.json` (user) or `.cursor/mcp.json` (project). Setup installs no skill for
  Cursor; the server's MCP instructions carry the vet guidance.
Setup appends one TOML table (Codex) or adds one key (Cursor) and keeps everything else in the
file; a file it cannot parse is left alone. The index is synced to `~/.skillfetch/index`.
Before anything changes, setup prints every path, file and command and asks. Nothing that
exists is overwritten: a different file or server entry is shown as a diff and left as it is.
`--remove` undoes what setup installed (only files and entries that still match what it would
install); the index is kept.
"""

from __future__ import annotations

import difflib
import json
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

SERVER_NAME = "skillfetch"
CLIENTS = ("claude-code", "codex", "cursor")
DEFAULT_FROM = "git+https://github.com/hyunlord/skillfetch"
SKILLS = {"vet": "skillfetch-vet", "router": "skillfetch-router"}
_ASSET_DIRS = {"vet": "vet-skill", "router": "router-skill"}
AUTO_NOTE = (
    "Auto-apply (per-task routing) is on. Measured: better than popular skills installed for "
    "good, not better than no skill; +62% cost per session on single tasks (numbers.md §26) "
    "and about 1.5x over six requests in one session (§28); clearly better only on a design task."
)
DEFAULTS_LINE = (
    "Defaults: check before install = on · find = on request · auto-apply (per-task routing) = "
    "{auto}"
)


def asset_skill(kind: str) -> str:
    """SKILL.md text of the vet or router skill: package data in a wheel, else the repo's
    assets/ (a source checkout)."""
    name = _ASSET_DIRS[kind]
    packaged = Path(__file__).parent / "_assets" / name / "SKILL.md"
    if packaged.is_file():
        return packaged.read_text()
    return (Path(__file__).resolve().parents[2] / "assets" / name / "SKILL.md").read_text()


Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


@dataclass
class Setup:
    scope: str = "user"  # "user" or "project"
    auto: bool = False
    client: str = "claude-code"  # one of CLIENTS
    home: Path = field(default_factory=Path.home)
    cwd: Path = field(default_factory=Path.cwd)
    source: str = DEFAULT_FROM  # where uvx installs skillfetch from, for the MCP server
    index_dir: Path | None = None
    sync: bool = True
    run: Runner = _run
    which: Callable[[str], str | None] = shutil.which
    do_sync: Callable[[Path], str] | None = None  # returns a one-line result
    out: Callable[[str], None] = print

    def __post_init__(self):
        if self.client not in CLIENTS:
            raise ValueError(f"unknown client {self.client!r}; one of {', '.join(CLIENTS)}")
        if self.index_dir is None:
            self.index_dir = self.home / ".skillfetch" / "index"

    # --- what setup installs -------------------------------------------------------------

    @property
    def _base(self) -> Path:
        return self.home if self.scope == "user" else self.cwd

    @property
    def skills_root(self) -> Path | None:
        if self.client == "claude-code":
            return self._base / ".claude" / "skills"
        if self.client == "codex":
            return self._base / ".agents" / "skills"
        return None  # Cursor: MCP only

    @property
    def config_file(self) -> Path:
        if self.client == "codex":
            return self._base / ".codex" / "config.toml"
        if self.client == "cursor":
            return self._base / ".cursor" / "mcp.json"
        return self.home / ".claude.json" if self.scope == "user" else self.cwd / ".mcp.json"

    def server_entry(self, auto: bool | None = None) -> dict:
        auto = self.auto if auto is None else auto
        args = ["--from", self.source, "skillfetch", "serve"] + ([] if auto else ["--vet"])
        if self.client == "claude-code":
            return {"type": "stdio", "command": "uvx", "args": args, "env": {}}
        return {"command": "uvx", "args": args}

    def skills(self) -> dict[str, str]:
        if self.skills_root is None:
            return {}
        kinds = ["vet", "router"] if self.auto else ["vet"]
        return {SKILLS[k]: asset_skill(k) for k in kinds}

    def toml_block(self, entry: dict | None = None) -> str:
        """The `[mcp_servers.skillfetch]` table setup appends to Codex's config.toml."""
        e = entry or self.server_entry()
        args = ", ".join(json.dumps(a) for a in e["args"])
        return (
            f"\n# added by `skillfetch setup --client codex`\n[mcp_servers.{SERVER_NAME}]\n"
            f"command = {json.dumps(e['command'])}\nargs = [{args}]\n"
        )

    def add_command(self) -> list[str]:
        e = self.server_entry()
        return [
            "claude",
            "mcp",
            "add",
            "-s",
            self.scope,
            SERVER_NAME,
            "--",
            e["command"],
            *e["args"],
        ]

    def remove_command(self) -> list[str]:
        return ["claude", "mcp", "remove", "-s", self.scope, SERVER_NAME]

    # --- reading what is there -----------------------------------------------------------

    def _read_config(self) -> dict | None:
        """The parsed config file: {} when it does not exist, None when it cannot be parsed."""
        try:
            text = self.config_file.read_text()
        except FileNotFoundError:
            return {}
        except OSError:
            return None
        try:
            data = tomllib.loads(text) if self.client == "codex" else json.loads(text)
        except (ValueError, tomllib.TOMLDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def current_entry(self) -> dict | None:
        data = self._read_config() or {}
        key = "mcp_servers" if self.client == "codex" else "mcpServers"
        servers = data.get(key)
        return servers.get(SERVER_NAME) if isinstance(servers, dict) else None

    def _register_action(self) -> tuple[str, object]:
        if self.client == "claude-code":
            return ("mcp", self.add_command())
        if self.client == "codex":
            return ("toml-append", (self.config_file, self.toml_block()))
        return ("json-merge", (self.config_file, self.server_entry()))

    def _register_text(self) -> list[str]:
        where = self._tilde(self.config_file)
        if self.client == "claude-code":
            return [
                f"- MCP server '{SERVER_NAME}': `{' '.join(self.add_command())}`",
                f"  (Claude Code writes it to {where})",
            ]
        if self.client == "codex":
            lines = [f"- MCP server '{SERVER_NAME}': append to {where}:"]
            lines += ["    " + x for x in self.toml_block().strip("\n").split("\n")]
            if self.scope == "project":
                lines.append(
                    "  (Codex reads a project's .codex/config.toml for trusted projects only)"
                )
            return lines
        entry = json.dumps({SERVER_NAME: self.server_entry()}, indent=2)
        lines = [f"- MCP server '{SERVER_NAME}': add to `mcpServers` in {where}:"]
        lines += ["    " + x for x in entry.split("\n")]
        lines.append("  (other servers in the file are kept)")
        return lines

    @staticmethod
    def _same_entry(a: dict, b: dict) -> bool:
        keys = ("command", "args")
        return all(a.get(k) == b.get(k) for k in keys)

    @staticmethod
    def _diff(old: str, new: str, old_name: str, new_name: str) -> str:
        lines = difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), old_name, new_name
        )
        return "".join(lines)

    # --- plan, then do -------------------------------------------------------------------

    def plan(self) -> tuple[list[str], list[tuple[str, object]]]:
        """(lines to show, actions). An action is ("skill", (path, text)), ("mcp", cmd) or
        ("sync", dest). Existing files and entries that differ are shown and not changed."""
        lines = [f"skillfetch setup ({self.client}, {self.scope} scope)", ""]
        actions: list[tuple[str, object]] = []
        entry, current = self.server_entry(), self.current_entry()
        if self.client != "claude-code" and self._read_config() is None:
            lines.append(
                f"- MCP server '{SERVER_NAME}': {self._tilde(self.config_file)} cannot be parsed; "
                "left as it is. Add this yourself:"
            )
            lines += self._register_text()[1:] or self._register_text()
        elif current is None:
            lines += self._register_text()
            actions.append(self._register_action())
        elif self._same_entry(current, entry):
            lines.append(f"- MCP server '{SERVER_NAME}': already registered, unchanged")
        else:
            old = json.dumps(current, indent=2, sort_keys=True) + "\n"
            new = json.dumps(entry, indent=2, sort_keys=True) + "\n"
            lines.append(
                f"- MCP server '{SERVER_NAME}': a different entry exists in "
                f"{self._tilde(self.config_file)}; left as it is (remove it with "
                "`skillfetch setup --remove`, or edit it):"
            )
            lines.append(self._diff(old, new, "existing", "setup would add").rstrip("\n"))
        if self.skills_root is None:
            lines.append(
                "- skills: none for Cursor; the server's MCP instructions tell the agent to scan "
                "before installing a skill and to find skills on request"
            )
        for name, text in self.skills().items():
            path = self.skills_root / name / "SKILL.md"
            if not path.exists():
                lines.append(f"- skill {name}: {self._tilde(path)}")
                actions.append(("skill", (path, text)))
            elif path.read_text() == text:
                lines.append(f"- skill {name}: already installed, unchanged")
            else:
                lines.append(f"- skill {name}: {self._tilde(path)} differs; left as it is:")
                diff = self._diff(path.read_text(), text, "existing", "setup would install")
                lines.append(diff.rstrip("\n"))
        if self.sync:
            lines.append(f"- index: `skillfetch sync` to {self._tilde(self.index_dir)}")
            actions.append(("sync", self.index_dir))
        lines += ["", DEFAULTS_LINE.format(auto="on" if self.auto else "off (--auto turns it on)")]
        if self.auto:
            lines.append(AUTO_NOTE)
        return lines, actions

    def apply(self, actions: list[tuple[str, object]]) -> int:
        failed = 0
        for kind, arg in actions:
            if kind == "skill":
                path, text = arg
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
                self.out(f"installed {self._tilde(path)}")
            elif kind == "mcp":
                if self.which("claude") is None:
                    self.out(
                        "skipped the MCP server: the `claude` CLI is not on PATH. Run:\n  "
                        + " ".join(arg)
                    )
                    failed += 1
                    continue
                proc = self.run(arg)
                if proc.returncode != 0:
                    self.out(f"`{' '.join(arg)}` failed: {(proc.stderr or proc.stdout).strip()}")
                    failed += 1
                else:
                    self.out(f"registered the MCP server '{SERVER_NAME}' ({self.scope} scope)")
            elif kind == "toml-append":
                path, block = arg
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a") as fh:
                    fh.write(block)
                self.out(f"added the MCP server '{SERVER_NAME}' to {self._tilde(path)}")
            elif kind == "json-merge":
                path, entry = arg
                data = self._read_config() or {}
                data.setdefault("mcpServers", {})[SERVER_NAME] = entry
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2) + "\n")
                self.out(f"added the MCP server '{SERVER_NAME}' to {self._tilde(path)}")
            elif kind == "sync":
                try:
                    self.out((self.do_sync or _default_sync)(arg))
                except Exception as exc:  # noqa: BLE001 - reported, setup goes on
                    self.out(f"index sync failed: {exc}; run `skillfetch sync` later")
                    failed += 1
        return failed

    def plan_remove(self) -> tuple[list[str], list[tuple[str, object]]]:
        lines = [f"skillfetch setup --remove ({self.client}, {self.scope} scope)", ""]
        actions: list[tuple[str, object]] = []
        current = self.current_entry()
        mine = [self.server_entry(auto=False), self.server_entry(auto=True)]
        where = self._tilde(self.config_file)
        if current is None:
            lines.append(f"- MCP server '{SERVER_NAME}': not registered")
        elif not any(self._same_entry(current, e) for e in mine):
            lines.append(f"- MCP server '{SERVER_NAME}': not the entry setup adds; left as it is")
        elif self.client == "claude-code":
            lines.append(f"- MCP server '{SERVER_NAME}': `{' '.join(self.remove_command())}`")
            actions.append(("mcp", self.remove_command()))
        elif self.client == "codex":
            text = self.config_file.read_text()
            block = next((b for b in (self.toml_block(e) for e in mine) if b in text), None)
            if block is None:
                lines.append(
                    f"- MCP server '{SERVER_NAME}': the table in {where} was edited after setup; "
                    "left as it is"
                )
            else:
                lines.append(f"- MCP server '{SERVER_NAME}': remove its table from {where}")
                actions.append(("toml-remove", (self.config_file, block)))
        else:
            lines.append(f"- MCP server '{SERVER_NAME}': remove it from `mcpServers` in {where}")
            actions.append(("json-remove", self.config_file))
        for kind, name in SKILLS.items():
            if self.skills_root is None:
                break
            path = self.skills_root / name / "SKILL.md"
            if not path.exists():
                continue
            if path.read_text() == asset_skill(kind):
                lines.append(f"- skill {name}: remove {self._tilde(path.parent)}")
                actions.append(("rmskill", path.parent))
            else:
                lines.append(f"- skill {name}: changed since setup; left as it is")
        lines += ["", f"The index at {self._tilde(self.index_dir)} is kept."]
        return lines, actions

    def apply_remove(self, actions: list[tuple[str, object]]) -> int:
        failed = 0
        for kind, arg in actions:
            if kind == "rmskill":
                shutil.rmtree(arg)
                self.out(f"removed {self._tilde(arg)}")
            elif kind == "toml-remove":
                path, block = arg
                path.write_text(path.read_text().replace(block, "", 1))
                self.out(f"removed the MCP server '{SERVER_NAME}' from {self._tilde(path)}")
            elif kind == "json-remove":
                data = self._read_config() or {}
                data.get("mcpServers", {}).pop(SERVER_NAME, None)
                arg.write_text(json.dumps(data, indent=2) + "\n")
                self.out(f"removed the MCP server '{SERVER_NAME}' from {self._tilde(arg)}")
            elif kind == "mcp":
                if self.which("claude") is None:
                    self.out("the `claude` CLI is not on PATH. Run:\n  " + " ".join(arg))
                    failed += 1
                    continue
                proc = self.run(arg)
                if proc.returncode != 0:
                    self.out(f"`{' '.join(arg)}` failed: {(proc.stderr or proc.stdout).strip()}")
                    failed += 1
                else:
                    self.out(f"removed the MCP server '{SERVER_NAME}' ({self.scope} scope)")
        return failed

    def _tilde(self, path: Path) -> str:
        try:
            return "~/" + path.relative_to(self.home).as_posix()
        except ValueError:
            return str(path)


def _default_sync(dest: Path) -> str:
    import os

    from skillfetch.index import sync as index_sync
    from skillfetch.index.loader import tilde

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    result = index_sync.sync(dest, token=token)
    state = "installed" if result.changed else "already up to date"
    return f"index {state}: {tilde(result.index.root)} ({len(result.index.records)} skills)"


def main(setup: Setup, remove: bool, yes: bool, ask: Callable[[str], str] = input) -> int:
    lines, actions = setup.plan_remove() if remove else setup.plan()
    setup.out("\n".join(lines))
    if not actions:
        setup.out("\nNothing to change.")
        return 0
    if not yes:
        try:
            answer = ask("\nProceed? [y/N] ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            setup.out("Nothing changed.")
            return 1
    failed = setup.apply_remove(actions) if remove else setup.apply(actions)
    return 1 if failed else 0
