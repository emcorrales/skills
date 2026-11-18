---
name: ai-native-sdlc-init
description: Set up the AI-native SDLC playbook in a repo as modular plays — intent/spec/plan artifacts per change, CLAUDE.md, feedback loop and guardrail hooks, approval gates, and optional PR review, CI, evals and metrics-driven maintenance. Team layout (committed) or a private --local layout that changes nothing teammates see.
argument-hint: "[target dir, default: current project] [plays: review,ci,evals,maintain] [--local]"
disable-model-invocation: true
---

# ai-native-sdlc-init: the AI-native SDLC playbook in one repo

Arguments: $ARGUMENTS (a target dir, default: the current project root; and optionally
which plays to add).

Source: Anthropic's *AI-native SDLC playbook* (article and Academy course). Its plays,
scaled down to one repo and one owner, who plays every human role (originator, product
owner, policy owner, code owner, release manager).

**The loop.** Each stage ends by committing an artifact the next stage reads, and
production feeds the next intent:

| Stage | Artifact | Gate (human) |
|---|---|---|
| 1 Plan | `intent/<date>-<slug>/intent.md` via `/intent` | accept / reject |
| 2 Design | `spec.md` beside it via `/spec` | go / no-go |
| 3 Build | plan mode → `plan.md` → code via `/implement` (bugs: `/fix`) | accept the plan |
| 4 Test | `verify/run.sh` (hooks, verifier agent, CI, evals) | — deterministic |
| 5 Deploy | PR reviewed per `REVIEW.md`; approval-gate hook | merge, release |
| 6 Maintain | band breach → draft `intent.md` (back to 1) | triage |

## Team or private layout

| | Team (default) | Private (`--local`) |
|---|---|---|
| For | repos where everyone uses the workflow | shared repos where only you do |
| Artifacts, verify, evals, bands, REVIEW.md | `intent/`, `verify/`, `evals/`, `sdlc/`, `REVIEW.md`, committed | all under `.sdlc/`, with its **own private git repo** for history |
| Skills, agents, hooks | `.claude/…`, committed | `.claude/…`, hidden via `.git/info/exclude` |
| Settings | `.claude/settings.json` | `.claude/settings.local.json` |
| Your notes and constraints | `CLAUDE.md` | `CLAUDE.local.md` (the team's CLAUDE.md is untouched) |
| Pre-commit | `.githooks/` + `core.hooksPath` | `.git/hooks/pre-commit` (skipped if a hooks manager owns hooks) |
| CI (`ci` play, workflows of `evals`/`maintain`) | GitHub Actions | not installed; run evals and band checks locally |

In the private layout `git status` stays clean, and nothing reaches a commit or a push.
The skills, hooks and scripts are the same; they detect the layout at runtime, and
the scaffold rewrites paths in the prose (`intent/…` → `.sdlc/intent/…`).
`sdlc/record.sh` (or `.sdlc/record.sh`) commits artifacts to the right history in either
layout. Choose private when teammates haven't adopted the workflow.

## Switching layouts
When the user asks to switch (the team adopts it, or stops using it):
```bash
python3 <this-skill-dir>/scripts/switch.py <target> --to shared|private --dry-run   # show the user
python3 <this-skill-dir>/scripts/switch.py <target> --to shared|private [--import-history]
```
It moves the files, rewrites their paths and moves settings entries. It also swaps the
pre-commit hook and the exclude list. It refuses to start if a destination exists or
both layouts are present. It stages the result and **never commits**, except that
`--import-history` with `--to shared` replays `.sdlc`'s intent history as commits on the
current branch (original authors and dates, so delivery metrics carry over). Ask before
using that flag: those commits are visible to the team.
- **→ shared:** afterwards, offer to move shareable parts of `CLAUDE.local.md` into
  `CLAUDE.md` (user decides what), and to add CI with `scaffold.py --plays ci,…`. The old
  private history is parked at `.git/sdlc-private-history.git`.
- **→ private:** it stages removal of the shared workflow files and of its GitHub
  workflows, since CI would break without `verify/`. Committing that removal is the
  user's call, and teammates will see it. Afterwards, offer to copy the workflow
  sections of `CLAUDE.md` into `CLAUDE.local.md`.
- Then run step 5's checks in the new layout and report what's staged.

**Advisory vs deterministic.** CLAUDE.md and skills are advisory: Claude can ignore them.
Hooks, `verify/run.sh`, CI and evals can't be ignored. Anything that must always hold
needs one of those, so most of the value is **real checks in `verify/run.sh`**.

## Plays

| Play | Installs | Needs |
|---|---|---|
| `core` (always) | `intent/`, `/intent` `/spec` `/implement` `/fix` skills, `verify/run.sh`, verifier agent, hooks (post-edit verify, guard, approval gate), pre-commit (secret scan + fast verify), `sdlc/delivery.py`, `.worktreeinclude`, settings | — |
| `review` | `REVIEW.md`, reviewer agent, `/sweep-pr` | `gh` for `/sweep-pr` |
| `ci` | `.github/workflows/verify.yml` (+ read-only triage of failed PR builds) | GitHub; a Claude secret for triage only |
| `evals` | `evals/run.py`, `evals/_example.json`, `agent-evals.yml` | real past tasks; Claude login locally, a secret in CI |
| `maintain` | `sdlc/bands.json`, `detect.py` (+ tests), `check.py`, CI-failure-rate metric, `maintain.yml` | GitHub Actions history (or your own metric source); a secret in CI |

The playbook's order: start with plays that have no prerequisites (core). Evals need a
working feedback loop and a few real tasks, CI/CD needs review and hooks, and closing the
loop needs CI and intent. Plays can be added later by running this skill again.

## Steps

### 1. Look before writing
- Resolve the target and confirm it's a git repo (if not, offer `git init`).
- Read: README, CLAUDE.md, `.claude/` (settings, hooks, agents, skills), CI config, and
  the build/test/lint setup (`package.json`, `Makefile`, `pyproject.toml`, …). Note which
  commands exist and how long they take, whether the remote is GitHub, and whether
  `gh` is authenticated.
- **Layout:** use `--local` if the user asks for a private or personal setup, or the repo
  is shared and they haven't said the team is adopting it. If unclear, ask (step 2).
- Existing pieces win: the scaffold never overwrites, so adapt to an existing
  `verify/run.sh`, hook, agent or skill of the same name instead of duplicating it.

### 2. Ask what you can't infer (one message, at most 3 questions)
Draft answers from the code first so the user just confirms:
- **Hard constraints:** rules never traded off (e.g. "no network calls", "Python 3.9",
  "no secrets in the repo").
- **Done when:** which checks prove it works, and which are fast enough for every edit.
- **Layout:** team or private (only if step 1 didn't settle it).
- **Plays:** recommend core plus whatever fits (GitHub remote → `ci`; 3+ merged tasks
  worth replaying → `evals`; review on every PR → `review`; Actions history or
  monitoring → `maintain`).

### 3. Scaffold
```bash
python3 <this-skill-dir>/scripts/scaffold.py --list
python3 <this-skill-dir>/scripts/scaffold.py <target> --plays <list> [--local] --dry-run   # show the user
python3 <this-skill-dir>/scripts/scaffold.py <target> --plays <list> [--local] [--name "<Project>"]
```
It reports CREATED / SKIPPED / MERGED for each file. Settings are merged, never replaced:
it adds missing keys and permission rules, plus hooks whose command isn't registered yet.
In team layout it sets `core.hooksPath=.githooks` only if unset. In private layout it
adds every created path to `.git/info/exclude` and creates `.sdlc/.git`. It also
refuses `ci`, which is only shared workflows. If the hooks path points elsewhere
(husky…), tell the user, and suggest calling `.githooks/pre-commit` from their hook.

### 4. Tailor (this is the real work)
Paths below are for the team layout; in the private layout `intent/`, `verify/`,
`evals/` and `REVIEW.md` sit under `.sdlc/`, and `sdlc/x` is `.sdlc/x`.

**private layout, first:** never edit tracked files: no edits to the team's CLAUDE.md,
CI or config. `verify/run.sh` wraps the commands the team already has (their test and
lint scripts); it doesn't add tooling to the repo. Put your hard constraints, workflow
and corrections in `CLAUDE.local.md`. For `maintain`, run `python3 .sdlc/check.py`
yourself, or schedule it locally (cron, `/loop`).

**core**
- **`verify/run.sh`:** one `step` per real check. Fast ones (lint, unit tests,
  constraint scans; ~1s total) go above the `if`, slow ones (e2e, build) inside it. Back
  each hard constraint with a check where possible, even a `grep`. A missing tool prints
  BLOCKED and fails. Use only commands that exist; run each once. Remove the "no checks"
  warning only once real steps exist.
- **`CLAUDE.md`** (private layout: `CLAUDE.local.md`, with only Hard constraints,
  Verifying your work, Workflow and Things Claude gets wrong, since the team's CLAUDE.md
  already covers the project. Rewrite the template's paths to `.sdlc/…`). Team layout: if missing, write it from `assets/CLAUDE-template.md` (as `/init`
  would, then cut it to a page). If present, merge in only the sections it lacks and
  leave the user's content alone. Fill in Commands with healthy output, and fill in Hard
  constraints. Remove the `<play: …>` placeholders for plays not installed, and keep the
  text of those that are.
- **`guard.sh`:** add generated or frozen paths to the deny list (`src/gen/*`,
  `vendor/*`). Adjust the "ask" list of check-defining files if the repo keeps its checks
  elsewhere.
- **`approval-gate.sh`:** replace the example deploy commands with the project's real
  release and publish commands.
- **`post-edit-verify.sh`:** adjust the skip list if markdown is a deliverable, or if
  generated files should be skipped.
- **`.worktreeinclude`:** add the git-ignored files `verify/run.sh` needs.
- **Skills (play 3.3):** if a policy must be applied the same way every time (an API
  rule, a security rule, a UI convention), offer to write it as
  `.claude/skills/<name>/SKILL.md`. Give it numbered rules and a check script, and back
  any rule that must hold with a verify step or a hook. Don't make a skill for what fits
  in CLAUDE.md.

**review:** fill in REVIEW.md's "Do not report" and "Needs a human" sections. For review
on every GitHub PR, tell the user to run `/install-github-app` themselves (it's
interactive and adds a secret), then point its review prompt at `REVIEW.md`.

**ci:** add the toolchain setup `verify/run.sh` needs. Not on GitHub? Port the one
`verify/run.sh` step to their CI and delete the file. Suggest making `verify` a required
check in branch protection.

**evals:** collect 3–5 real tasks to start (the playbook's target is 20–50 over time),
from merged PRs or fixed incidents. For each, write `evals/<name>.json` from
`_example.json`:
- `from`: the commit before the task was done;
- `prompt`: the task as it was asked;
- `may_change`: the paths the task may touch;
- `checks`: behavioral checks, not code style. Helper scripts go in `evals/helpers/`.

Run `python3 evals/run.py` once and show the result; it runs Claude, so confirm with the
user before running it. Each production incident should add an eval.

**maintain:** keep `ci_failure_rate` if the repo has Actions history, and add a band for
each metric the project really has: a script that prints readings as JSON. Keep 2σ
read-only. 3σ acts only through `routes` that are pre-approved and reversible: a draft
PR, or a rollback runbook. Add `step "band detection tests" python3 sdlc/test_detect.py` to the fast section of
`verify/run.sh`. Run
`python3 sdlc/check.py --dry-run` and show the output.

### 5. Verify the setup
- `verify/run.sh --fast` and `verify/run.sh` both end in `VERIFY PASSED`.
- Feed each hook a fake payload. A matching payload should print a JSON decision (or
  exit 2 for post-edit), and a harmless one should print nothing:
  ```bash
  echo '{"cwd":"'"$PWD"'","tool_input":{"command":"git push --force"}}' | .claude/hooks/approval-gate.sh   # ask
  echo '{"cwd":"'"$PWD"'","tool_input":{"command":"git status"}}'       | .claude/hooks/approval-gate.sh   # nothing
  echo '{"tool_input":{"file_path":"'"$PWD"'/verify/run.sh"}}'          | .claude/hooks/guard.sh           # ask
  echo '{"tool_input":{"file_path":"'"$PWD"'/<a source file>"}}'        | .claude/hooks/guard.sh           # nothing
  echo '{"tool_input":{"file_path":"'"$PWD"'/<a source file>"}}'        | .claude/hooks/post-edit-verify.sh; echo $?  # 0
  ```
- `python3 sdlc/delivery.py` runs (it prints "No intent/<change>/ folders" on a new setup).
- Private layout: `git status --porcelain` prints nothing. (Hook paths in the commands
  above become `.sdlc/verify/run.sh` and so on.)

### 6. Report
- What was created, skipped and merged, and which plays are installed.
- The checks now in `verify/run.sh`, and which hard constraints have no automated check.
- Gated commands and guarded paths.
- What still needs the user: secrets, `/install-github-app`, branch protection, eval
  tasks, metric sources.
- Settings and hooks take effect in a new Claude Code session, or after `/hooks` reloads
  them.
- The first move: `/intent <next change>`.

Team layout: don't commit unless asked. If asked, put everything in one commit ("Set up
AI-native SDLC"). Private layout: there is nothing to commit in the project; the setup
is already recorded in `.sdlc/`'s own history.
