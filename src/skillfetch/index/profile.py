"""profile_repo: languages, frameworks and package managers from manifest files only.

Reads files at the repo root — package.json, pyproject.toml, requirements.txt, go.mod,
Cargo.toml, lockfiles and framework config files. Never opens source files.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

# dependency name -> framework tag
JS_FRAMEWORKS = {
    "react": "react",
    "next": "nextjs",
    "vue": "vue",
    "nuxt": "nuxt",
    "svelte": "svelte",
    "@sveltejs/kit": "sveltekit",
    "@angular/core": "angular",
    "express": "express",
    "@nestjs/core": "nestjs",
    "react-native": "react-native",
    "electron": "electron",
    "tailwindcss": "tailwind",
    "vite": "vite",
    "jest": "jest",
    "vitest": "vitest",
}
PY_FRAMEWORKS = {
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "sqlalchemy": "sqlalchemy",
    "pytest": "pytest",
    "torch": "pytorch",
    "tensorflow": "tensorflow",
    "pandas": "pandas",
}
GO_FRAMEWORKS = {
    "github.com/gin-gonic/gin": "gin",
    "github.com/labstack/echo": "echo",
    "github.com/gofiber/fiber": "fiber",
}
RUST_FRAMEWORKS = {"tokio": "tokio", "axum": "axum", "actix-web": "actix", "serde": "serde"}
LOCKFILES = {
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lockb": "bun",
    "bun.lock": "bun",
    "uv.lock": "uv",
    "poetry.lock": "poetry",
    "Pipfile": "pipenv",
    "pdm.lock": "pdm",
    "requirements.txt": "pip",
    "Cargo.lock": "cargo",
    "go.sum": "go modules",
}
# config file prefix -> framework tag
CONFIG_FILES = {
    "next.config.": "nextjs",
    "vite.config.": "vite",
    "nuxt.config.": "nuxt",
    "svelte.config.": "svelte",
    "astro.config.": "astro",
    "tailwind.config.": "tailwind",
    "angular.json": "angular",
    "tsconfig.json": None,  # language marker, below
}
_PY_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _py_names(requirements: list[str]) -> set[str]:
    out = set()
    for line in requirements:
        if m := _PY_NAME.match(line):
            out.add(m.group(1).lower().replace("_", "-"))
    return out


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(errors="replace"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(errors="replace"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def profile_repo(path: Path) -> dict:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return {"path": str(root), "error": "not a directory"}
    names = {p.name for p in root.iterdir() if p.is_file()}
    languages, frameworks, managers, seen = set(), set(), set(), []

    if "package.json" in names:
        seen.append("package.json")
        pkg = _read_json(root / "package.json")
        deps = {
            **(pkg.get("dependencies") or {}),
            **(pkg.get("devDependencies") or {}),
            **(pkg.get("peerDependencies") or {}),
        }
        languages.add("javascript")
        if "typescript" in deps or "tsconfig.json" in names:
            languages.add("typescript")
        frameworks |= {tag for dep, tag in JS_FRAMEWORKS.items() if dep in deps}
        if isinstance(pkg.get("packageManager"), str):
            managers.add(pkg["packageManager"].split("@", 1)[0])
    if "pyproject.toml" in names:
        seen.append("pyproject.toml")
        data = _read_toml(root / "pyproject.toml")
        project = data.get("project") or {}
        deps = list(project.get("dependencies") or [])
        for extra in (project.get("optional-dependencies") or {}).values():
            deps += list(extra)
        for group in (data.get("dependency-groups") or {}).values():
            deps += [d for d in group if isinstance(d, str)]
        poetry = (data.get("tool") or {}).get("poetry") or {}
        deps += list((poetry.get("dependencies") or {}).keys())
        languages.add("python")
        found = _py_names(deps)
        frameworks |= {tag for dep, tag in PY_FRAMEWORKS.items() if dep in found}
        if poetry:
            managers.add("poetry")
        if "uv" in (data.get("tool") or {}):
            managers.add("uv")
    if "requirements.txt" in names:
        seen.append("requirements.txt")
        languages.add("python")
        found = _py_names((root / "requirements.txt").read_text(errors="replace").splitlines())
        frameworks |= {tag for dep, tag in PY_FRAMEWORKS.items() if dep in found}
    if "go.mod" in names:
        seen.append("go.mod")
        languages.add("go")
        text = (root / "go.mod").read_text(errors="replace")
        frameworks |= {tag for mod, tag in GO_FRAMEWORKS.items() if mod in text}
    if "Cargo.toml" in names:
        seen.append("Cargo.toml")
        languages.add("rust")
        data = _read_toml(root / "Cargo.toml")
        deps = {**(data.get("dependencies") or {}), **(data.get("dev-dependencies") or {})}
        frameworks |= {tag for dep, tag in RUST_FRAMEWORKS.items() if dep in deps}
    for name, manager in LOCKFILES.items():
        if name in names:
            managers.add(manager)
            seen.append(name)
    for prefix, tag in CONFIG_FILES.items():
        for name in sorted(n for n in names if n.startswith(prefix)):
            seen.append(name)
            if tag:
                frameworks.add(tag)
            elif name == "tsconfig.json":
                languages.add("typescript")
    tags = sorted(languages | frameworks | managers)
    return {
        "path": str(root),
        "languages": sorted(languages),
        "frameworks": sorted(frameworks),
        "package_managers": sorted(managers),
        "tags": tags,
        "manifests": sorted(set(seen)),
    }
