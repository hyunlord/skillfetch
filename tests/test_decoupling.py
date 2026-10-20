"""Runtime halves must not import a model client (CLAUDE.md working rules)."""

import ast
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
