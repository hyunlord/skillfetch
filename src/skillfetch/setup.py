"""`skillfetch setup [--auto] [--project | --user] [--remove]`: one command for the three
features (README, "Setup").

- **Check before install** (on): the vet skill (`assets/vet-skill`) and an MCP server with
  `scan_skill` and `find_skills` (`serve --vet`).
- **Find on request** (on): `find_skills`, the same server and skill.
- **Auto-apply, per-task routing** (off): `--auto` installs the router skill and serves the
  routing tools too (`serve` without `--vet`).

The MCP server is registered with Claude Code's own `claude mcp add -s <scope>`, which writes
`~/.claude.json` (user scope) or `.mcp.json` (project scope); setup only reads those files to
compare. Skills go to `~/.claude/skills/` or `./.claude/skills/`. The index is synced to
`~/.skillfetch/index`. Before anything changes, setup prints every path, file and command and
asks. Nothing that exists is overwritten: a different file or server entry is shown as a diff
and left as it is. `--remove` undoes what setup installed (only files and entries that still
match what it would install); the index is kept.
"""

from __future__ import annotations

import difflib
import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

SERVER_NAME = "skillfetch"
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
        if self.index_dir is None:
            self.index_dir = self.home / ".skillfetch" / "index"

    # --- what setup installs -------------------------------------------------------------

    @property
    def skills_root(self) -> Path:
        base = self.home if self.scope == "user" else self.cwd
        return base / ".claude" / "skills"

    @property
    def config_file(self) -> Path:
        return self.home / ".claude.json" if self.scope == "user" else self.cwd / ".mcp.json"

    def server_entry(self, auto: bool | None = None) -> dict:
        auto = self.auto if auto is None else auto
        args = ["--from", self.source, "skillfetch", "serve"] + ([] if auto else ["--vet"])
        return {"type": "stdio", "command": "uvx", "args": args, "env": {}}

    def skills(self) -> dict[str, str]:
        kinds = ["vet", "router"] if self.auto else ["vet"]
        return {SKILLS[k]: asset_skill(k) for k in kinds}

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

    def current_entry(self) -> dict | None:
        try:
            data = json.loads(self.config_file.read_text())
        except (OSError, ValueError):
            return None
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        return (servers or {}).get(SERVER_NAME)

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
        lines = [f"skillfetch setup ({self.scope} scope)", ""]
        actions: list[tuple[str, object]] = []
        entry, current = self.server_entry(), self.current_entry()
        cmd = " ".join(self.add_command())
        if current is None:
            lines.append(f"- MCP server '{SERVER_NAME}': `{cmd}`")
            lines.append(f"  (Claude Code writes it to {self._tilde(self.config_file)})")
            actions.append(("mcp", self.add_command()))
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
            elif kind == "sync":
                try:
                    self.out((self.do_sync or _default_sync)(arg))
                except Exception as exc:  # noqa: BLE001 - reported, setup goes on
                    self.out(f"index sync failed: {exc}; run `skillfetch sync` later")
                    failed += 1
        return failed

    def plan_remove(self) -> tuple[list[str], list[tuple[str, object]]]:
        lines = [f"skillfetch setup --remove ({self.scope} scope)", ""]
        actions: list[tuple[str, object]] = []
        current = self.current_entry()
        mine = [self.server_entry(auto=False), self.server_entry(auto=True)]
        if current is None:
            lines.append(f"- MCP server '{SERVER_NAME}': not registered")
        elif any(self._same_entry(current, e) for e in mine):
            lines.append(f"- MCP server '{SERVER_NAME}': `{' '.join(self.remove_command())}`")
            actions.append(("mcp", self.remove_command()))
        else:
            lines.append(f"- MCP server '{SERVER_NAME}': not the entry setup adds; left as it is")
        for kind, name in SKILLS.items():
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
