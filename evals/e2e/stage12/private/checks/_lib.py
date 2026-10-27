"""Shared utilities for Stage 12 hidden checks.

Every check is called as ``check.py <worktree> <outdir> --base <base-commit>`` and compares the
committed HEAD of <worktree> with <base>. Rule items test one Northwind rule each. Functional items
test the requested behaviour only and must pass for any plain, correct implementation (no Northwind
field names, helpers or formats).
"""
import json
import os
import re
import subprocess
import sys
import textwrap


# --- git diff helpers ---
def get_changed_files(worktree, base):
    r = subprocess.run(["git", "-C", worktree, "diff", "--name-only", base, "HEAD"],
                       capture_output=True, text=True)
    return [f for f in r.stdout.strip().split("\n") if f]


def get_added_lines(worktree, base):
    r = subprocess.run(["git", "-C", worktree, "diff", "-U0", base, "HEAD"],
                       capture_output=True, text=True)
    lines, cur = [], None
    for ln in r.stdout.split("\n"):
        if ln.startswith("+++ "):
            cur = ln[6:] if ln.startswith("+++ b/") else None
        elif ln.startswith("+") and not ln.startswith("+++"):
            lines.append((cur, ln[1:]))
    return lines


def added_text_by_file(worktree, base):
    out = {}
    for f, ln in get_added_lines(worktree, base):
        if f:
            out.setdefault(f, []).append(ln)
    return {f: "\n".join(v) for f, v in out.items()}


def read_file(worktree, path):
    full = os.path.join(worktree, path)
    if not os.path.isfile(full):
        return None
    with open(full, encoding="utf-8", errors="replace") as f:
        return f.read()


def file_exists(worktree, path):
    return os.path.isfile(os.path.join(worktree, path))


def _app_code(f):
    """Non-test application source (Python) outside the provided lib/ helpers."""
    return bool(f) and f.endswith(".py") and not f.startswith(("tests/", "lib/"))


def _check_added_lines(worktree, base, pattern, exclude_paths=("tests/", "lib/")):
    """Pattern appears in an added line of the diff (outside excluded paths), or, for a call written over several
    lines (`event(\n    "a.b", ...)`), in a file's added lines joined with newlines (added 2026-10-27, pilot)."""
    for f, ln in get_added_lines(worktree, base):
        if f and not any(f.startswith(p) for p in exclude_paths):
            if re.search(pattern, ln):
                return True, f"Found in {f}: {ln.strip()[:80]}"
    for f, text in added_text_by_file(worktree, base).items():
        if not any(f.startswith(p) for p in exclude_paths):
            m = re.search(pattern, text)
            if m:
                return True, f"Found in {f} (multi-line): {' '.join(m.group(0).split())[:80]}"
    return False, "Not found in added lines"


# --- changelog ---
def check_changelog(worktree, base):
    for f in get_changed_files(worktree, base):
        if f.startswith("changes/") and f.endswith(".md"):
            if re.match(r"^(feat|fix|chore)-[a-z0-9]+(-[a-z0-9]+)*\.md$", os.path.basename(f)):
                return True, f"Found {f}"
    return False, "No changes/<feat|fix|chore>-<slug>.md fragment"


# --- api/routes.toml ---
def check_routes_toml(worktree, method, path):
    content = read_file(worktree, "api/routes.toml")
    if not content:
        return False, "api/routes.toml missing or empty"
    norm = lambda p: re.sub(r"\{[^}]+\}", "{}", p.rstrip("/") or "/")
    for blk in re.split(r"\[\[routes\]\]", content)[1:]:
        m = re.search(r'method\s*=\s*"([^"]+)"', blk)
        p = re.search(r'path\s*=\s*"([^"]+)"', blk)
        has_owner = re.search(r"^\s*owner\s*=", blk, re.M)
        has_rate = re.search(r"^\s*rate_limit\s*=", blk, re.M)
        if m and p and m.group(1).upper() == method.upper() and norm(p.group(1)) == norm(path):
            if has_owner and has_rate:
                return True, f"Found {method} {path} with owner and rate_limit"
            return False, f"{method} {path} entry lacks owner or rate_limit"
    return False, f"No {method} {path} entry in api/routes.toml"


# --- errors/catalog.yaml ---
NW_CODE = r"NW-[A-Z]+-\d{3}"


def check_new_catalog_entry(worktree, base):
    content = read_file(worktree, "errors/catalog.yaml") or ""
    old = subprocess.run(["git", "-C", worktree, "show", f"{base}:errors/catalog.yaml"],
                         capture_output=True, text=True)
    old_codes = set(re.findall(NW_CODE, old.stdout)) if old.returncode == 0 else set()
    new_codes = set(re.findall(NW_CODE, content)) - old_codes
    if new_codes:
        return True, f"New codes: {sorted(new_codes)}"
    return False, "No new NW-<AREA>-<NNN> code in errors/catalog.yaml"


def is_nw_error_body(body):
    if not isinstance(body, dict) or not isinstance(body.get("error"), dict):
        return False
    e = body["error"]
    return bool(isinstance(e.get("code"), str) and re.fullmatch(NW_CODE, e["code"])
                and isinstance(e.get("message"), str) and e.get("trace_id"))


def check_nw_error_format_static(worktree, base):
    ok, d = _check_added_lines(worktree, base, r"""["']""" + NW_CODE + r"""["']""")
    if ok and _check_added_lines(worktree, base, r"""["']error["']\s*:""")[0] \
            and _check_added_lines(worktree, base, r"""["']trace_id["']""")[0]:
        return True, "static: " + d
    return False, "static: no NW error envelope in added code"


# --- deploy/CHECKLIST.md ---
def check_deploy_checklist(worktree, base):
    content = read_file(worktree, "deploy/CHECKLIST.md") or ""
    m = re.search(r"^##\s*\[?Unreleased\]?\s*$(.*?)(?=^##\s|\Z)", content, re.M | re.S)
    if not m:
        return False, "No '## Unreleased' section in deploy/CHECKLIST.md"
    section = [l.strip() for l in m.group(1).splitlines() if l.strip().startswith(("-", "*"))]
    added = {ln.strip() for f, ln in get_added_lines(worktree, base) if f == "deploy/CHECKLIST.md"}
    new = [l for l in section if l in added]
    if new:
        return True, new[0][:80]
    return False, "No new item under '## Unreleased'"


# --- config/ENV.md ---
def check_env_md(worktree, base):
    for f, ln in get_added_lines(worktree, base):
        if f == "config/ENV.md" and re.search(r"NW_ORDERS_[A-Z0-9_]+", ln):
            return True, ln.strip()[:80]
    return False, "No NW_ORDERS_ entry added to config/ENV.md"


# --- flags/registry.toml ---
def check_flags_registry(worktree, base):
    content = read_file(worktree, "flags/registry.toml") or ""
    added = "\n".join(ln for f, ln in get_added_lines(worktree, base) if f == "flags/registry.toml")
    for blk in re.split(r"\[\[flags\]\]", content)[1:]:
        name = re.search(r'^\s*name\s*=\s*"([a-z0-9_]+\.[a-z0-9_]+)"', blk, re.M)
        if name and name.group(0).strip() in added and re.search(r"^\s*owner\s*=", blk, re.M) \
                and re.search(r"^\s*expires\s*=", blk, re.M):
            return True, f"Flag {name.group(1)} with owner and expires"
    return False, "No new [[flags]] entry with <team>.<flag> name, owner and expires"


# --- db/migrations ---
def _new_sql_files(worktree, base):
    return [f for f in get_changed_files(worktree, base) if f.endswith(".sql") and file_exists(worktree, f)]


def check_migration_file(worktree, base):
    for f in _new_sql_files(worktree, base):
        if re.match(r"^V\d{8}_\d{2}__[a-z0-9]+(_[a-z0-9]+)*\.sql$", os.path.basename(f)):
            return True, f"Found {f}"
    return False, "No migration named V<YYYYMMDD>_<NN>__<snake>.sql"


def check_migration_rollback(worktree, base):
    for f in _new_sql_files(worktree, base):
        content = read_file(worktree, f) or ""
        m = list(re.finditer(r"^--\s*rollback:", content, re.M))
        if m:
            tail = content[m[-1].end():]
            if re.search(r"\b(ALTER|DROP|DELETE|UPDATE|CREATE)\b", tail, re.I):
                return True, f"Rollback section at end of {f}"
    return False, "No '-- rollback:' section with reverse SQL at the end of a migration"


def check_migration_in_dir(worktree, base):
    for f in _new_sql_files(worktree, base):
        if f.startswith("db/migrations/"):
            return True, f
    return False, "No new .sql file under db/migrations/"


# --- Python source rules ---
def check_nwlog_in_new_code(worktree, base):
    if not _check_added_lines(worktree, base, r"from lib\.nwlog import|from lib import nwlog|import lib\.nwlog")[0]:
        return False, "lib.nwlog not imported in added code"
    return _check_added_lines(worktree, base, r"""\b(nwlog[_.])?event\s*\(\s*["'][a-z0-9_]+\.[a-z0-9_]+["']""")


def check_no_print_logging(worktree, base):
    for f, ln in get_added_lines(worktree, base):
        if _app_code(f):
            if re.search(r"(^|[^\w.])print\s*\(", ln):
                return False, f"{f}: print() in added line"
            if re.search(r"\blogging\.\w+\s*\(|\blogger\.\w+\s*\(|getLogger\s*\(", ln):
                return False, f"{f}: logging call in added line"
    return True, "No print/logging in added app code"


def check_nwids_in_new_code(worktree, base):
    return _check_added_lines(worktree, base, r"nwids[_.]new\s*\(|from lib\.nwids import|import lib\.nwids")


def check_flags_in_new_code(worktree, base):
    if not _check_added_lines(worktree, base, r"from lib\.flags import|from lib import flags|import lib\.flags")[0]:
        return False, "lib.flags not imported in added code"
    return _check_added_lines(worktree, base, r"""\b(flags[_.])?is_on\s*\(\s*["'][a-z0-9_]+\.[a-z0-9_]+["']""")


def check_settings_get(worktree, base):
    imported = _check_added_lines(worktree, base, r"from lib\.settings import|from lib import settings|import lib\.settings")[0]
    called = _check_added_lines(worktree, base, r"""(?:settings[_.]get|(?<![.\w])get)\s*\(\s*["'][A-Z0-9_]+["']""")
    if imported and called[0]:
        return True, called[1]
    return False, "No settings.get('<KEY>') call through lib.settings"


def check_no_direct_environ(worktree, base):
    for f, ln in get_added_lines(worktree, base):
        if _app_code(f) and re.search(r"os\.environ|os\.getenv|getenv\s*\(|BaseSettings", ln):
            return False, f"{f}: direct environment access"
    return True, "No direct environment access in added app code"


def check_money_minor(worktree, base):
    added = "\n".join(ln for f, ln in get_added_lines(worktree, base) if _app_code(f))
    if re.search(r"amount_minor\s*:\s*float|amount_minor\s+REAL", added):
        return False, "amount_minor typed as float/REAL"
    if "amount_minor" in added and "currency" in added:
        return True, "amount_minor and currency in added code"
    return False, "No amount_minor + currency in added code"


# --- Python test conventions ---
def _new_test_files(worktree, base):
    return [f for f in get_changed_files(worktree, base)
            if f.startswith("tests/") and f.endswith(".py") and file_exists(worktree, f)]


def check_test_filename(worktree, base):
    for f in _new_test_files(worktree, base):
        if re.match(r"^test_[a-z0-9]+(_[a-z0-9]+)*__[a-z0-9]+(_[a-z0-9]+)*\.py$", os.path.basename(f)):
            return True, f"Found {f}"
    return False, "No test file named test_<module>__<behavior>.py"


def check_nw_factory_used(worktree, base):
    for f in _new_test_files(worktree, base):
        if re.search(r"def test_\w+\([^)]*\bnw_factory\b", read_file(worktree, f) or ""):
            return True, f"nw_factory fixture requested in {f}"
    return False, "No new test requests the nw_factory fixture"


def check_contract_marker(worktree, base):
    for f in _new_test_files(worktree, base):
        if re.search(r"@pytest\.mark\.contract\b", read_file(worktree, f) or ""):
            return True, f"@pytest.mark.contract in {f}"
    return False, "No @pytest.mark.contract in new tests"


# --- response helpers ---
TS_VALUE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
RFC3339Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
PUBLIC_ID = re.compile(r"^[a-z][a-z0-9]*_[0-9A-Za-z]{10,}$")


def first_list(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        if isinstance(body.get("data"), list):
            return body["data"]
        for v in body.values():
            if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                return v
    return None


def dicts_in(body):
    """The body and every nested dict, outermost first."""
    out, stack = [], [body]
    while stack:
        x = stack.pop(0)
        if isinstance(x, dict):
            out.append(x)
            stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
        elif isinstance(x, list):
            stack.extend(v for v in x if isinstance(v, (dict, list)))
    return out


def timestamp_fields(obj):
    if not isinstance(obj, dict):
        return []
    return [(k, v) for k, v in obj.items() if isinstance(v, str) and TS_VALUE.match(v)]


def check_ts_at_suffix(obj):
    ts = timestamp_fields(obj)
    if not ts:
        return False, "No timestamp fields in response"
    bad = [k for k, _ in ts if not k.endswith("_at")]
    if bad:
        return False, f"Timestamp fields without _at: {bad}"
    return True, f"All timestamp fields use _at: {[k for k, _ in ts]}"


def check_ts_rfc3339z(obj):
    ts = timestamp_fields(obj)
    if not ts:
        return False, "No timestamp fields in response"
    bad = [f"{k}={v}" for k, v in ts if not RFC3339Z.match(v)]
    if bad:
        return False, f"Not UTC RFC 3339 with Z: {bad}"
    return True, f"RFC 3339 Z: {[k for k, _ in ts]}"


# --- Python runtime ---
def ensure_venv(worktree):
    if not os.path.isdir(os.path.join(worktree, ".venv")):
        subprocess.run(["uv", "sync", "--quiet"], cwd=worktree, capture_output=True, timeout=300)


def run_pytest(worktree):
    worktree = os.path.abspath(worktree)
    ensure_venv(worktree)
    py = os.path.join(worktree, ".venv", "bin", "pytest")
    if not os.path.isfile(py):
        py = "pytest"
    r = subprocess.run([py, "-q", "--tb=short", "-p", "no:cacheprovider"], cwd=worktree,
                       capture_output=True, text=True, timeout=300)
    summary = [l for l in r.stdout.splitlines() if re.search(r"\b(passed|failed|error|no tests ran)\b", l)]
    return r.returncode == 0, (summary[-1] if summary else "") + " | " + (r.stdout + r.stderr)[-300:]


_PRELUDE = '''
import io, json, os, sqlite3, sys, tempfile
WT = {wt!r}
sys.path.insert(0, WT)
os.chdir(WT)
DB = os.path.join(tempfile.mkdtemp(prefix="s12chk_"), "check.db")
os.environ["DATABASE_URL"] = DB
_real_stdout = sys.stdout
sys.stdout = io.StringIO()
out = {{}}


def q(sql, args=()):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return [dict(x) for x in con.execute(sql, args).fetchall()]
    finally:
        con.close()


def x(sql, args=()):
    con = sqlite3.connect(DB)
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


try:
    from orders.database import init_db
    init_db()
    from fastapi.testclient import TestClient
    from orders.app import app
    with TestClient(app, raise_server_exceptions=False) as c:
        def call(method, path, **kw):
            r = c.request(method, path, **kw)
            try:
                body = r.json()
            except Exception:
                body = r.text[:300]
            return r.status_code, body
{body}
except BaseException as e:
    out["_error"] = repr(e)[:500]
sys.stdout = _real_stdout
print("@@RESULT@@" + json.dumps(out, default=str))
'''


def run_app_script(worktree, body, timeout=120):
    """Run <body> against the app in a fresh temp DB. <body> sees call(), q(), x(), out."""
    worktree = os.path.abspath(worktree)
    ensure_venv(worktree)
    py = os.path.join(worktree, ".venv", "bin", "python")
    if not os.path.isfile(py):
        py = sys.executable
    script = _PRELUDE.format(wt=os.path.abspath(worktree),
                             body=textwrap.indent(textwrap.dedent(body), " " * 8))
    try:
        r = subprocess.run([py, "-c", script], capture_output=True, text=True, timeout=timeout,
                           cwd=worktree)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    for line in reversed(r.stdout.splitlines()):
        if line.startswith("@@RESULT@@"):
            res = json.loads(line[len("@@RESULT@@"):])
            return res, res.get("_error", "")
    return None, (r.stdout[-300:] + r.stderr[-300:])


# --- Web: text helpers ---
WEB_CODE = (".tsx", ".jsx", ".ts", ".js", ".css", ".scss")
WEB_SKIP = ("styles/tokens.css", "analytics/events.ts", "lib/", "next-env.d.ts", "node_modules/")


def _web_added(worktree, base, exts=WEB_CODE):
    return {f: t for f, t in added_text_by_file(worktree, base).items()
            if f.endswith(exts) and not f.startswith(WEB_SKIP)}


LETTERS = re.compile(r"[^\W\d_]{2,}")


CODE_LIKE = (r"[=;()\[\]]|&&|\|\||\s\?\s|\b(return|const|let|var|function|import|export|from|else|if|"
             r"try|catch|finally|case|default|as|type|interface|extends|await|async|new|typeof)\b")


def hardcoded_strings(text):
    """User-visible literal text in JSX: text nodes, visible attributes, confirm()/alert() strings."""
    hits = []
    t = re.sub(r"&\w+;", " ", text)
    t = re.sub(r"`[^`]*`", "``", t)
    t = re.sub(r"\{/\*.*?\*/\}", " ", t, flags=re.S)
    for m in re.finditer(r"[>}]([^<>{}]*)[<{]", t):
        s = m.group(1).strip()
        if s and LETTERS.search(s) and not re.search(CODE_LIKE, s):
            hits.append(s[:40])
    for m in re.finditer(r"""\b(title|placeholder|alt|aria-label|label)\s*=\s*["']([^"']+)["']""", t):
        if LETTERS.search(m.group(2)):
            hits.append(f"{m.group(1)}={m.group(2)[:40]}")
    for m in re.finditer(r"""\b(confirm|alert)\s*\(\s*["'`]([^"'`]+)""", t):
        if LETTERS.search(m.group(2)):
            hits.append(f"{m.group(1)}({m.group(2)[:40]})")
    return hits


I18N_IMPORT = re.compile(r"""import\s*\{([^}]*)\}\s*from\s*['"][^'"]*i18n['"]""")


def t_call_names(content):
    """Names whose calls count as t() calls in one file (scope fixed 2026-10-27, DESIGN §11):
    - t imported from an i18n module: `import { t } from '../lib/i18n'`, or an alias `import { t as tx } ...`;
    - a wrapper defined in the same file whose body calls one of those names with the wrapper's first parameter passed
      through unchanged as the first argument: `const tr = (key) => t(key, locale)`, `function tr(key) { return t(key) }`.
    A local function named t that is not imported from i18n does not count. Call sites still need a literal key."""
    names = set()
    for m in I18N_IMPORT.finditer(content):
        for spec in m.group(1).split(","):
            parts = spec.split()
            if parts and parts[0] == "t":
                names.add(parts[2] if len(parts) == 3 and parts[1] == "as" else "t")
    if not names:
        return names
    alt = "|".join(re.escape(n) for n in sorted(names))
    defs = [
        # const tr = (key: string, ...) => <expr or block>      /  const tr = key => ...
        r"""\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s*)?\(?\s*([A-Za-z_$][\w$]*)[^)=]*\)?\s*(?::\s*[^=]+?)?=>""",
        # function tr(key: string, ...) {
        r"""\bfunction\s+([A-Za-z_$][\w$]*)\s*\(\s*([A-Za-z_$][\w$]*)""",
    ]
    for pat in defs:
        for m in re.finditer(pat, content):
            name, param = m.group(1), m.group(2)
            if name in names:
                continue
            body = content[m.end():m.end() + 400]
            if pat.startswith(r"\bfunction"):
                brace = content.find("{", m.end())
                body = content[brace:brace + 400] if brace != -1 else ""
            if re.match(r"""\s*(?:\{\s*return\s+)?(?:""" + alt + r""")\(\s*""" + re.escape(param) + r"""\s*[,)]""",
                        body):
                names.add(name)
    return names


def t_keys_in(text, names):
    """Literal keys passed to any of `names` in `text`."""
    if not names:
        return []
    alt = "|".join(re.escape(n) for n in sorted(names))
    return re.findall(r"""(?<![\w$.])(?:""" + alt + r""")\(\s*['"`]([\w.-]+)['"`]""", text)


def check_web_t_usage(worktree, base):
    added = _web_added(worktree, base, (".tsx", ".jsx"))
    used = False
    for f, text in added.items():
        names = t_call_names(read_file(worktree, f) or "")
        if t_keys_in(text, names):
            used = True
    if not used:
        return False, "No t() calls (imported from lib/i18n) in added JSX"
    hits = [h for text in added.values() for h in hardcoded_strings(text)]
    if hits:
        return False, f"Hardcoded user-visible strings: {hits[:5]}"
    return True, "t() used, no hardcoded user-visible strings"


def check_web_locale_keys(worktree, base):
    keys = set()
    for f, text in _web_added(worktree, base, (".tsx", ".jsx", ".ts", ".js")).items():
        keys.update(t_keys_in(text, t_call_names(read_file(worktree, f) or "")))
    if not keys:
        return False, "No t() keys in added code"
    try:
        en = json.loads(read_file(worktree, "locales/en.json") or "")
        ko = json.loads(read_file(worktree, "locales/ko.json") or "")
    except json.JSONDecodeError:
        return False, "Missing or invalid locale JSON"

    def resolve(d, key):
        if isinstance(d, dict) and isinstance(d.get(key), str):
            return d[key]
        for p in key.split("."):
            if not isinstance(d, dict) or p not in d:
                return None
            d = d[p]
        return d if isinstance(d, str) else None

    bad_fmt = [k for k in keys if not re.fullmatch(r"[A-Za-z0-9_]+\.[A-Za-z0-9_.]+", k)]
    missing_en = sorted(k for k in keys if resolve(en, k) is None)
    missing_ko = sorted(k for k in keys if resolve(ko, k) is None)
    if missing_en or missing_ko or bad_fmt:
        return False, f"Missing en:{missing_en[:5]} ko:{missing_ko[:5]} bad_format:{bad_fmt[:5]}"
    return True, f"All {len(keys)} keys in both locales"


HEX = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b")
RAW_SPACING = re.compile(
    r"""\b(?:padding|margin|gap|rowGap|columnGap|row-gap|column-gap)[\w-]*\s*[:=]\s*"""
    r"""(?:["'][^"'\n]*?\b\d+(?:\.\d+)?(?:px|rem|em)\b|[^;"'\n,}]*?\b[1-9]\d*(?:\.\d+)?(?:px|rem|em)\b|[1-9]\d*\s*[,}\n])""")


def _style_scan(worktree, base):
    added = _web_added(worktree, base)
    joined = "\n".join(added.values())
    return {
        "color_token": "var(--nw-color-" in joined,
        "spacing_token": "var(--nw-spacing-" in joined,
        "raw_hex": sorted(set(HEX.findall(joined)))[:5],
        "raw_spacing": [m.group(0)[:40] for m in RAW_SPACING.finditer(joined)][:5],
    }


def check_web_tokens_color(worktree, base):
    s = _style_scan(worktree, base)
    if s["raw_hex"]:
        return False, f"Raw hex colors: {s['raw_hex']}"
    if not s["color_token"]:
        return False, "No var(--nw-color-*) tokens"
    return True, "Colors use tokens, no raw hex"


def check_web_tokens_spacing(worktree, base):
    s = _style_scan(worktree, base)
    if s["raw_spacing"]:
        return False, f"Raw spacing: {s['raw_spacing']}"
    if not s["spacing_token"]:
        return False, "No var(--nw-spacing-*) tokens"
    return True, "Spacing uses tokens"


def _tracked_events(worktree, base):
    events_ts = read_file(worktree, "analytics/events.ts") or ""
    consts = dict(re.findall(r"""(\w+)\s*:\s*['"]([\w.-]+)['"]""", events_ts))
    names, imported = set(), False
    for f, text in _web_added(worktree, base, (".tsx", ".jsx", ".ts", ".js")).items():
        content = read_file(worktree, f) or ""
        if re.search(r"""import\s*\{[^}]*\btrack\b[^}]*\}\s*from\s*['"][^'"]*analytics['"]""", content):
            imported = True
        names.update(re.findall(r"""\btrack\(\s*['"`]([\w.-]+)['"`]""", text))
        for key in re.findall(r"""\btrack\(\s*EVENTS\.(\w+)""", text):
            names.add(consts.get(key, f"<undeclared EVENTS.{key}>"))
    return names, imported, events_ts


def check_web_track_call(worktree, base):
    names, imported, _ = _tracked_events(worktree, base)
    if not imported or not names:
        return False, "No track() call imported from lib/analytics"
    bad = [n for n in names if not re.fullmatch(r"[a-z0-9]+_[a-z0-9_]+", n)]
    if bad:
        return False, f"Event names not <page>_<action>: {bad}"
    return True, f"track() events: {sorted(names)}"


def check_web_event_declared(worktree, base):
    names, _, events_ts = _tracked_events(worktree, base)
    if not names:
        return False, "No track() events in added code"
    declared = set(re.findall(r"""['"]([\w.-]+)['"]""", events_ts))
    missing = sorted(n for n in names if n not in declared)
    if missing:
        return False, f"Undeclared events: {missing}"
    return True, f"All events declared: {sorted(names)}"


# --- Web runtime ---
def ensure_node_modules(worktree):
    if not os.path.isdir(os.path.join(worktree, "node_modules")):
        subprocess.run(["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"], cwd=worktree,
                       capture_output=True, timeout=600)


def run_next_build(worktree):
    worktree = os.path.abspath(worktree)
    ensure_node_modules(worktree)
    r = subprocess.run(["npm", "run", "build"], cwd=worktree, capture_output=True, text=True,
                       timeout=600, env={**os.environ, "NEXT_TELEMETRY_DISABLED": "1"})
    return r.returncode == 0, f"npm run build exit={r.returncode} | " + (r.stdout + r.stderr)[-400:]


# --- Output ---
def item(item_id, ok, detail):
    return {"id": item_id, "pass": ok, "detail": str(detail)[:300]}


def write_result(outdir, task_id, rule_items, functional_items):
    result = {
        "task_id": task_id,
        "rule_pass": sum(1 for r in rule_items if r["pass"] is True),
        "rule_total": len(rule_items),
        "rule_undecidable": sum(1 for r in rule_items if r["pass"] is None),
        "func_pass": sum(1 for f in functional_items if f["pass"] is True),
        "func_total": len(functional_items),
        "rule_items": rule_items,
        "functional_items": functional_items,
    }
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "check.json"), "w") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    return result
