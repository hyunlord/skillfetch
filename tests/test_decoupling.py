"""Runtime halves must not import a model client (CLAUDE.md working rules)."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "src" / "skillfetch"
RUNTIME_PACKAGES = ("index", "resolve", "mcp")
FORBIDDEN = {"anthropic", "openai"}


def _runtime_files():
    for pkg in RUNTIME_PACKAGES:
        yield from sorted((SRC / pkg).rglob("*.py"))


@pytest.mark.parametrize("path", list(_runtime_files()), ids=lambda p: str(p.relative_to(SRC)))
def test_no_model_client_imports(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        for name in names:
            assert name.split(".")[0] not in FORBIDDEN, f"{path}: imports {name}"


@pytest.mark.parametrize("module", ["skillfetch.mcp.server", "skillfetch.cli"])
def test_runtime_entry_points_do_not_load_a_model_client(module):
    """The static check above misses transitive imports (runtime → ingest → client). Import
    the entry point in a fresh interpreter and look at what actually got loaded."""
    code = (
        f"import sys, {module}; print(sorted(m for m in {sorted(FORBIDDEN)!r} if m in sys.modules))"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "[]", f"{module} loads {proc.stdout.strip()}"
