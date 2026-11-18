#!/usr/bin/env python3
"""Continuous evals for the agent configuration (CLAUDE.md, .claude/**).

    python3 evals/run.py [name ...] [--min-pass 1.0] [--out results.json] [--keep]

Each evals/<name>.json (files starting with "_" are skipped) is a real past task:
  name          short id
  source        the PR or incident it came from
  from          commit the run starts from (before the task was done)
  prompt        what the agent is asked to do
  may_change    globs of paths the run may touch; anything else fails the eval
  checks        [{"name": ..., "run": "<shell>"}]; each must exit 0
  allowed_tools optional, default "Read,Edit,Write,Glob,Grep,Bash(verify/run.sh:*)"
  timeout       optional seconds for the agent run, default 900

For each eval: a scratch git worktree at `from`; evals/ and the old agent config are
removed from it and the CURRENT CLAUDE.md and .claude/ (the config under test) copied
in and committed; `claude -p` runs there; then the grading happens from outside the
agent's workspace. The agent can't pass by editing the checks: evals/ isn't in its
workspace, and changes outside may_change fail the run. An empty or errored agent
result is a failure. Checks run in the scratch dir with EVAL_BASE (the commit before the
agent ran), EVAL_HELPERS (this evals/ dir), EVAL_SCRATCH and EVAL_VERIFY (the verify
script to grade with) set. In the private layout .sdlc/ is untracked, so the run gets a
copy of .sdlc/verify for its feedback loop, and grading uses the original.
Never pass --bare to claude here: it skips CLAUDE.md, skills and hooks, the files under test.
"""
import argparse, fnmatch, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent.name == ".sdlc"    # private layout: .sdlc/evals/, untracked
ROOT = HERE.parent.parent if LOCAL else HERE.parent
VERIFY_REL = ".sdlc/verify/run.sh" if LOCAL else "verify/run.sh"
DEFAULT_TOOLS = f"Read,Edit,Write,Glob,Grep,Bash({VERIFY_REL}:*)"


def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def run_eval(spec: dict, keep: bool) -> dict:
    res = {"name": spec["name"], "source": spec.get("source"), "pass": False, "failures": []}
    scratch = Path(tempfile.mkdtemp(prefix=f"eval-{spec['name']}-"))
    r = sh(["git", "worktree", "add", "--detach", str(scratch), spec["from"]], ROOT)
    if r.returncode:
        res["failures"].append(f"worktree at {spec['from']}: {r.stderr.strip()}")
        return res
    try:
        for p in ("evals", ".claude", "CLAUDE.md", "CLAUDE.local.md"):
            t = scratch / p
            shutil.rmtree(t) if t.is_dir() else t.unlink(missing_ok=True)
        for f in ("CLAUDE.md", "CLAUDE.local.md"):
            if (ROOT / f).exists():
                shutil.copy2(ROOT / f, scratch / f)
        if (ROOT / ".claude").is_dir():
            shutil.copytree(ROOT / ".claude", scratch / ".claude",
                            ignore=shutil.ignore_patterns("worktrees"))
        if LOCAL and (ROOT / ".sdlc/verify").is_dir():
            shutil.copytree(ROOT / ".sdlc/verify", scratch / ".sdlc/verify")
        sh(["git", "add", "-A"], scratch)
        sh(["git", "-c", "user.name=evals", "-c", "user.email=evals@localhost", "commit",
            "-q", "--no-verify", "--allow-empty", "-m", "eval: config under test"], scratch)
        base = sh(["git", "rev-parse", "HEAD"], scratch).stdout.strip()

        t0 = time.time()
        try:
            r = sh(["claude", "-p", spec["prompt"], "--allowedTools",
                    spec.get("allowed_tools", DEFAULT_TOOLS), "--output-format", "json"],
                   scratch, timeout=spec.get("timeout", 900))
            out = json.loads(r.stdout or "{}")
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            out = {"is_error": True, "result": f"{type(e).__name__}"}
        res["seconds"] = round(time.time() - t0)
        res["cost_usd"] = out.get("total_cost_usd")
        if out.get("is_error") or not str(out.get("result", "")).strip():
            res["failures"].append(f"agent run empty or errored: {str(out.get('result',''))[:200]}")

        changed = set(sh(["git", "diff", "--name-only", base], scratch).stdout.split())
        changed |= set(sh(["git", "ls-files", "--others", "--exclude-standard"], scratch).stdout.split())
        allowed = spec.get("may_change", [])
        outside = sorted(p for p in changed if not any(fnmatch.fnmatch(p, g) for g in allowed))
        if outside:
            res["failures"].append(f"changed outside may_change: {', '.join(outside)}")
        res["changed"] = sorted(changed)

        verify = (ROOT if LOCAL else scratch) / VERIFY_REL
        env = {**os.environ, "EVAL_BASE": base, "EVAL_HELPERS": str(HERE),
               "EVAL_SCRATCH": str(scratch), "EVAL_VERIFY": str(verify)}
        for chk in spec.get("checks", []):
            r = subprocess.run(chk["run"], shell=True, cwd=scratch, env=env,
                               capture_output=True, text=True)
            if r.returncode:
                tail = (r.stdout + r.stderr).strip().splitlines()[-5:]
                res["failures"].append(f"check '{chk['name']}' failed: " + " | ".join(tail))
        if not spec.get("checks"):
            res["failures"].append("no checks defined")
        res["pass"] = not res["failures"]
        return res
    finally:
        if keep:
            res["scratch"] = str(scratch)
        else:
            sh(["git", "worktree", "remove", "--force", str(scratch)], ROOT)
            shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="*")
    ap.add_argument("--min-pass", type=float, default=1.0, help="pass-rate threshold (default: every eval)")
    ap.add_argument("--out", help="write results JSON here")
    ap.add_argument("--keep", action="store_true", help="keep scratch worktrees for debugging")
    a = ap.parse_args()
    if not shutil.which("claude"):
        print("BLOCKED: claude CLI not found"); return 1
    specs = [json.loads(p.read_text()) for p in sorted(HERE.glob("*.json")) if not p.name.startswith("_")]
    if a.names:
        specs = [s for s in specs if s["name"] in a.names]
        if not specs:
            print(f"No evals named {', '.join(a.names)}."); return 1
    if not specs:
        print(f"No evals yet: add {HERE.relative_to(ROOT)}/<name>.json (see _example.json)."); return 0
    results = []
    for s in specs:
        r = run_eval(s, a.keep)
        results.append(r)
        print(("PASS  " if r["pass"] else "FAIL  ") + r["name"])
        for f in r["failures"]:
            print("      " + f)
    rate = sum(r["pass"] for r in results) / len(results)
    print(f"EVALS {sum(r['pass'] for r in results)}/{len(results)} passed ({rate:.0%}; threshold {a.min_pass:.0%})")
    if a.out:
        Path(a.out).write_text(json.dumps({"time": int(time.time()), "pass_rate": rate, "results": results}, indent=2))
    return 0 if rate >= a.min_pass else 1


if __name__ == "__main__":
    sys.exit(main())
