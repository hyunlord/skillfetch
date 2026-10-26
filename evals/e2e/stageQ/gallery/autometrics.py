"""Automatic per-output metrics for gallery v2, from a run's diff only (no model calls):
  tests_added    test functions added: lines starting with "+" (not "+++") that declare a test, by language —
                 Python `def test_…` / `async def test_…`; Rust `#[test]` / `#[tokio::test]` (the attribute line);
                 JS/TS `it(` / `test(` at line start; Go `func Test…(`; Java `@Test`; Swift `func test…(`
  readme         a README* file changed (any directory)
  deps           a dependency manifest or lockfile changed (pyproject.toml, requirements*.txt, uv.lock, package.json,
                 package-lock.json, bun.lock*, yarn.lock, pnpm-lock.yaml, Cargo.toml, Cargo.lock, go.mod, go.sum,
                 pom.xml, build.gradle*, Package.swift, Package.resolved)
  files / added / deleted   from the diff headers and +/- lines (lockfiles included)
Also file_finals(): the final text of a file after the run, rebuilt from the start-commit text plus the run's hunks."""
import re

TEST = [re.compile(p) for p in (r"^\s*(async\s+)?def\s+test_\w*\s*\(", r"^\s*#\[(tokio::)?test(\(.*\))?\]", r"^\s*(it|test)\s*\(",
                                r"^\s*func\s+Test\w*\s*\(", r"^\s*@Test\b", r"^\s*func\s+test\w*\s*\(")]
DEPS = re.compile(r"(^|/)(pyproject\.toml|requirements[^/]*\.txt|uv\.lock|package\.json|package-lock\.json|bun\.lockb?|yarn\.lock|"
                  r"pnpm-lock\.yaml|Cargo\.toml|Cargo\.lock|go\.mod|go\.sum|pom\.xml|build\.gradle(\.kts)?|Package\.swift|Package\.resolved)$")


def split(diff):
    """{path: chunk} for each file in a git diff."""
    out = {}
    for ch in re.split(r"(?=^diff --git )", diff, flags=re.M):
        m = re.match(r"diff --git a/(.*?) b/(.*)$", ch.split("\n", 1)[0])
        if m:
            out[m.group(2)] = ch
    return out


def metrics(diff):
    files = split(diff)
    added = deleted = tests = 0
    for f, ch in files.items():
        for l in ch.split("\n"):
            if l.startswith("+") and not l.startswith("+++"):
                added += 1
                tests += any(p.match(l[1:]) for p in TEST)
            elif l.startswith("-") and not l.startswith("---"):
                deleted += 1
    return {"tests_added": tests, "readme": any(re.search(r"(^|/)README[^/]*$", f, re.I) for f in files),
            "deps": sorted(f for f in files if DEPS.search(f)), "files": len(files), "added": added, "deleted": deleted,
            "paths": sorted(files)}


def apply_chunk(base_text, chunk):
    """The file's text after applying one file chunk of a unified diff to base_text ("" for a new file)."""
    if "\ndeleted file mode" in chunk.split("@@")[0]:
        return None
    src = base_text.split("\n") if base_text else []
    out, i = [], 0
    for h in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n((?:(?![@]{2} ).*\n?)*)", chunk, re.M):
        start = int(h.group(1)) - (0 if h.group(2) == "0" else 1)
        out += src[i:start]
        i = start
        for l in h.group(5).split("\n"):
            if l.startswith("\\"):
                continue
            if l.startswith("+"):
                out.append(l[1:])
            elif l.startswith("-"):
                i += 1
            elif l.startswith(" "):
                out.append(l[1:])
                i += 1
    out += src[i:]
    return "\n".join(out)
