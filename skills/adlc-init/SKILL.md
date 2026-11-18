---
name: adlc-init
description: Set up the AI-native development lifecycle (intent → spec → plan → build → verify) in a repo. It scaffolds intent.md, a /spec skill and template, a read-only verifier agent, a post-edit verify hook, a git pre-commit hook, docs/specs and docs/plans, and a CLAUDE.md workflow section, then wires verify/run.sh to the project's real checks. Use it when the user wants to "set up ADLC/SDLC", "add the spec/plan/verify workflow", "bootstrap Claude Code for this project", "add a verifier and hooks", or starts a new project and wants the same workflow as their other repos, even if they don't say "ADLC".
argument-hint: "[target dir, default: current project]"
---

# adlc-init: set up the AI-native dev lifecycle in a repo

Target: $ARGUMENTS (empty means the current project root).

This gives a repo a disciplined loop:
1. **Intent:** `intent.md` holds the goal, hard constraints, "done" and out of scope.
2. **Spec:** `/spec` checks a change against the intent and stops for go/no-go.
3. **Plan:** plan mode, with plans saved to `docs/plans/`.
4. **Build → verify:** a single `verify/run.sh` is the definition of done. A post-edit hook
   and a pre-commit hook run its `--fast` mode, and the `verifier` agent runs the full
   check from a fresh context.

Advice in CLAUDE.md and skills can be ignored. The hooks and `verify/run.sh` can't. So
most of the value comes from **real checks in `verify/run.sh`**. Scaffolding without
them is just ceremony, so spend your effort there.

## Steps

### 1. Look before writing
- Resolve the target and confirm it's a git repo (if not, offer `git init`).
- Read what's there: README, CLAUDE.md, any existing `.claude/` (settings, hooks, agents,
  skills), `intent.md`, and the build/test/lint setup (`package.json` scripts, `Makefile`,
  `pyproject.toml`, CI config). Note which test, lint, typecheck and build commands
  actually exist and how long they take.
- If the repo already has a `verify/run.sh`, a `spec` skill or a `verifier` agent, keep
  them. The scaffold never overwrites, and you should adapt to what's there rather than
  duplicate it.

### 2. Ask what you can't infer (one message, at most 3 questions)
Draft the answers from the README and code first, so the user only confirms or corrects:
- **Goal and users:** one or two sentences.
- **Hard constraints:** rules never traded off (e.g. "no network calls", "Python 3.9
  compatible", "no secrets in the repo").
- **Done when:** which checks prove it works, and which are fast enough for every edit.

### 3. Scaffold
```bash
python3 <this-skill-dir>/scripts/scaffold.py <target> --dry-run   # show the user first
python3 <this-skill-dir>/scripts/scaffold.py <target> [--name "<Project name>"]
```
It copies the files listed below without overwriting anything, merges the hook and
`plansDirectory` into `.claude/settings.json`, and sets `core.hooksPath` if it's unset.
Its output lists CREATED / SKIPPED / MERGED for each file. If `core.hooksPath` already
points elsewhere (husky, for example), it leaves it alone. Tell the user, and suggest
calling `verify/run.sh --fast` from their existing pre-commit hook.

| File | Purpose |
|---|---|
| `intent.md` | stage 1: goal, constraints, done, out of scope |
| `.claude/skills/spec/` | `/spec` skill and template (user-invoked only) |
| `.claude/agents/verifier.md` | read-only verifier that runs `verify/run.sh` |
| `.claude/hooks/post-edit-verify.sh` | runs `verify/run.sh --fast` after Claude's edits; exit 2 feeds failures back |
| `.githooks/pre-commit` | same fast check for edits made outside Claude |
| `verify/run.sh` | the stub to fill in: `step "<label>" <cmd>` lines, fast and full sections |
| `docs/specs/`, `docs/plans/` | where specs and plans go |
| `.worktreeinclude` | git-ignored files that worktrees need |

### 4. Tailor it (this is the real work)
- **`intent.md`:** fill it in from step 2. Keep it under a page.
- **`verify/run.sh`:** add a `step` per real check. Put fast ones (lint, unit tests, a
  scan of the constraints, ideally ~1s total) above the `if`, and slow ones (e2e,
  browser, full build) inside it. Back each hard constraint with a check where you can,
  even a small `grep` or script in `verify/`. A check that can't run (a missing tool)
  should print BLOCKED and fail. Only use commands that exist in the repo: run each one
  once to confirm. Remove the "no checks configured" warning only when real steps exist.
- **The spec template's constraint table:** one row per hard constraint in `intent.md`.
- **The post-edit hook's skip list:** the `case` line that skips docs and markdown. Adjust
  it if markdown is a deliverable, or if generated files should be skipped.
- **`CLAUDE.md`:** if it doesn't exist, create a short one: a project overview, a
  "Hard constraints" list that mirrors `intent.md`, then the contents of
  `assets/CLAUDE-workflow.md`. If it exists, merge in only the sections it lacks
  (Verify, Workflow, Things Claude gets wrong here). Don't rewrite the user's content.
  Keep it under a page.
- **`.worktreeinclude`:** list git-ignored files that `verify/run.sh` needs (`.env.local`,
  `node_modules/**`, large local fixtures).

### 5. Verify the setup itself
Run `verify/run.sh --fast` and `verify/run.sh`, and show the output. Both should end in
`VERIFY PASSED`. Then check that the hook fires: make a harmless edit to a watched file
and confirm the hook runs, or pipe a fake payload into it:
`echo '{"tool_input":{"file_path":"<abs path to a watched file>"}}' | .claude/hooks/post-edit-verify.sh; echo $?`

### 6. Report
List what was created, skipped and merged. Show the checks now in `verify/run.sh` and
which constraints have no automated check yet. Say that settings and hook changes take
effect in a new Claude Code session, or after `/hooks` reloads them. Don't commit unless
asked. When the user does commit, everything goes in one commit ("Set up AI-native dev
workflow").
