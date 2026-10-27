#!/usr/bin/env python3
"""Stage 12 (stage12/DESIGN.md §3): one session = (task, A|R|O, tag), E1 only. The Stage 11 harness
(stage11/scripts/run_s11.py) unchanged, with these settings swapped in before its main() runs:
  - tasks: stage12-private/tasks.jsonl (T1–T8 on nw-a, C1–C2 on nw-b; repos/nw-orders, repos/nw-web)
  - A: the task's start branch, no MCP
  - R: branch s12-r-<base> = start branch + shipped router S-b′ (sha 3efef1e0…f040, one commit "chore: add project
       skill"); MCP = skillfetch serve (server c55d561, default options) on stage12-private/index-nw
  - O: the start branch, no MCP; the first user message = stage12-private/o-prompts/<task>.md (the task's required
       Northwind skills in the exact load_skills output format from index-nw) + a blank line + the task prompt.
       Same place as R's loaded skills (the conversation, not the system prompt); only the choosing step differs
       (DESIGN §3, changed 2026-10-27 at the user's request).
  Stage 12b (stage12b/DESIGN.md §1, added 2026-10-27; A, R, O unchanged):
  - Rp (R′): branch s12b-rp-<base> = start branch + the org router variant (sha 3fbc33ad…cc27) + .skillfetch.yaml
       (sha 2b2ec10e…1f1e), one commit "chore: add project skill"; MCP = server feat/org-baseline@2ee8f77 on index-nw
  - N: branch s12b-n-<base> = start branch + the 24 Northwind SKILL.md under .claude/skills/<name>/ (FROZEN bytes), one
       commit "chore: add project skills"; no router, no MCP
  - F: the start branch, no MCP; the first user message = stage12-private/f-prompt/F.md (all 24 bodies) + the prompt
  - checks: stage12-private/checks/<task>/check.py <worktree> <outdir> --base <base>  -> <outdir>/check.json
  - outputs: stage12-private/runs/<cond>/<task>-<tag>.*; session directories ~/skillfetch-e2e-wt/s12/<random id>
usage: run_12.py <task_id> <A|R|O|Rp|N|F> <tag> [--dry-run [--no-prep]]"""
import hashlib
import json
import sys
from pathlib import Path

S12 = Path(__file__).resolve().parents[1]
E2E = S12.parent
PRIV = E2E / "stage12-private"
sys.path.insert(0, str(E2E / "stage11" / "scripts"))
import run_s11 as base  # noqa: E402

ROUTER_SHA = "3efef1e0b7cf5181fa1911f4ebd075cb5d8b8865926d6353399221392bf8f040"
ORG_SHA = "3fbc33adac90304235a4407bfcd6420d468ad39b66090c4a7fee3b9eb74ecc27"  # Stage 12b R′ router (PR #97 org.md)
YAML_SHA = "2b2ec10e61ee75ef9e129cfea0cbd16f8758b73c12b7234694be1cf76cd61f1e"
ORG_SERVER = Path.home() / "skillfetch-e2e-wt" / "s12b-server" / "2ee8f77"
NW_SKILLS = PRIV / "northwind-skills"
_orig_clone, _orig_preflight, _orig_build = base.clone, base.preflight, base.build_cmd


def load_tasks():
    out = {}
    for line in (PRIV / "tasks.jsonl").open():  # private until the experiment ends (DESIGN §9.1)
        t = json.loads(line)
        t["group"] = "T" if t["id"].startswith("T") else "C"  # T1–T8 not inferable, C1–C2 controls
        t["bundle"] = 4  # run_s11.main() allows condition A only in bundle 4; Stage 12 runs A in every task
        t.setdefault("check", "s12")
        out[t["id"]] = t
    return out


def snapshot_commit(wt):
    """The Stage 12 checks read `git diff <base> HEAD` (as the refs were validated: patch applied and committed), but a
    session usually leaves its work uncommitted. After the diff is collected and before the check, commit the working
    tree as is (same excludes as the collected diff). Found in the pilot, 2026-10-27 (DESIGN §11)."""
    from run_task import DIFF_EXCLUDES
    base.sh(["git", "add", "-A", "--", ".", *DIFF_EXCLUDES], cwd=wt)
    if base.sh(["git", "diff", "--cached", "--quiet"], cwd=wt).returncode == 0:
        return None
    env = {**base.env_s11(), "GIT_AUTHOR_NAME": "e2e", "GIT_AUTHOR_EMAIL": "e2e@local",
           "GIT_COMMITTER_NAME": "e2e", "GIT_COMMITTER_EMAIL": "e2e@local"}
    base.sh(["git", "commit", "-q", "--no-verify", "-m", "s12: check snapshot"], cwd=wt, env=env, check=True)
    return base.git(wt, "rev-parse", "HEAD")


def run_check(task, wt, b, out):
    noise = base.rs.strip_env_noise(wt)
    snap = snapshot_commit(wt)
    cdir = Path(str(out) + ".check")
    cmd = ["python3", str(PRIV / "checks" / task["id"] / "check.py"), str(wt), str(cdir), "--base", b]
    p = base.sh(cmd, env=base.env_s11(), timeout=3600)
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "run_check.log").write_text((p.stdout + p.stderr).replace(str(wt), "<wt>"))
    cj = cdir / "check.json"
    res = json.loads(cj.read_text()) if cj.exists() else {"pass": None, "error": f"check rc={p.returncode}"}
    res["env_noise_removed"] = noise
    res["snapshot_commit"] = snap
    return res


def configure(cond, task_id):
    tasks = load_tasks()
    t = tasks[task_id]
    base.PRIV = PRIV
    base.LOCK = PRIV / "runs" / "screenshot.lock"
    base.WT_ROOT = Path.home() / "skillfetch-e2e-wt" / "s12"
    base.SERVER = Path.home() / "skillfetch-e2e-wt" / "s26-server" / "c55d561"
    none = S12 / "mcp" / "mcp-none.json"
    base.MCP = {"A": none, "O": none, "R": S12 / "mcp" / "mcp-r.json", "Rp": S12 / "mcp" / "mcp-rp.json", "N": none, "F": none}
    base.COND_BRANCH = f"s12-r-{t['base_branch']}"
    base.ROUTER_SHA256 = ROUTER_SHA
    base.load_tasks = load_tasks
    base.run_check = run_check
    base.clone, base.build_cmd, base.preflight = _orig_clone, _orig_build, _orig_preflight  # reset per configure
    bb = t["base_branch"]
    if cond == "Rp":
        configure_rp(bb)
    elif cond == "N":
        configure_n(bb)
    if cond in ("O", "F"):  # same tree as A; the skills arrive as a prefix of the first user message
        base.clone = lambda task, c, wt: _orig_clone(task, "A", wt)
        prompt = (PRIV / "o-prompts" / f"{task_id}.md" if cond == "O" else PRIV / "f-prompt" / "F.md").read_text()

        def build_cmd(task, c, out):
            cmd = _orig_build(task, "A", out)
            assert cmd[:2] == ["claude", "-p"]
            cmd[2] = prompt.rstrip("\n") + "\n\n" + cmd[2]
            return cmd
        base.build_cmd = build_cmd


def _branch_problems(repo, base_ref, branch, want_files, msg):
    """The 12b branch is one commit on the start commit that adds exactly `want_files` {path: sha256}."""
    probs = []
    g = lambda *a: base.git(repo, *a, check=False)  # noqa: E731
    if g("rev-parse", f"{branch}^") != g("rev-parse", base_ref):
        probs.append(f"{branch} parent is not {base_ref}")
    if sorted(g("diff", "--name-only", base_ref, branch).splitlines()) != sorted(want_files):
        probs.append(f"{branch} changes other files than {len(want_files)} expected")
    for path, sha in want_files.items():
        blob = base.subprocess.run(["git", "-C", str(repo), "show", f"{branch}:{path}"], capture_output=True).stdout
        if hashlib.sha256(blob).hexdigest() != sha:
            probs.append(f"{branch}:{path} sha256 mismatch")
    if g("log", "-1", "--format=%s", branch) != msg:
        probs.append(f"{branch} commit message is not {msg!r}")
    return probs


def configure_rp(bb):
    base.COND_BRANCH, base.ROUTER_SHA256, base.SERVER = f"s12b-rp-{bb}", ORG_SHA, ORG_SERVER

    def preflight(task, c):
        probs, facts = _orig_preflight(task, c)
        probs = [p for p in probs if "changes more than the router file" not in p]  # R′ adds .skillfetch.yaml too
        probs += _branch_problems(E2E / "repos" / task["repo"], task["base_branch"], base.COND_BRANCH,
                                  {base.ROUTER_PATH: ORG_SHA, ".skillfetch.yaml": YAML_SHA}, base.ROUTER_MSG)
        return probs, facts
    base.preflight = preflight  # clone: the stock R path (router sha = ORG_SHA, skills = base + router file)


def configure_n(bb):
    want = {f".claude/skills/{d.name}/SKILL.md": hashlib.sha256((d / "SKILL.md").read_bytes()).hexdigest()
            for d in sorted(NW_SKILLS.iterdir()) if (d / "SKILL.md").exists()}
    assert len(want) == 24

    def preflight(task, c):
        probs, facts = _orig_preflight(task, "A")  # generic checks (index, tools, leftovers); s12-r is still valid
        probs += _branch_problems(E2E / "repos" / task["repo"], task["base_branch"], f"s12b-n-{bb}", want,
                                  "chore: add project skills")
        return probs, facts

    def clone(task, c, wt):
        base.COND_BRANCH = f"s12b-n-{bb}"
        facts = _orig_clone(task, "R", wt)  # stock clone of the condition branch; its router check does not apply
        base.COND_BRANCH = f"s12-r-{bb}"
        want_skills = sorted(facts["base_skills_files"] + list(want))
        facts["ok"] = (facts["refs"] == ["refs/heads/main"] and not facts["remotes"] and not facts["status"]
                       and facts["unreachable_objects"] == 0 and facts["router_sha256"] is None
                       and facts["skills_files"] == want_skills)
        return facts
    base.preflight, base.clone = preflight, clone


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    assert len(pos) == 3 and pos[1] in ("A", "R", "O", "Rp", "N", "F"), __doc__
    configure(pos[1], pos[0])
    base.main()
