# {{PROJECT_NAME}}
<!-- Private layout: this becomes CLAUDE.local.md, keep only Hard constraints,
     Verifying your work, Workflow and Things Claude gets wrong, with paths under .sdlc/. -->

<One or two sentences: what this is and who uses it.>

## Commands
<!-- One command per check, each exits non-zero on failure. Show healthy output. -->
- Verify everything: `verify/run.sh` → last line `VERIFY PASSED`
- Verify fast (run by hooks on every edit and commit): `verify/run.sh --fast`
- Build: `…` · Test: `…` · Lint: `…` · Run: `…`

## Conventions
<!-- Only what a new joiner needs on day one: language/framework, test expectations,
     formats. Anything long that must be applied consistently is a skill instead. -->

## Architecture
<!-- Directory roles, which component may call which, limits worth knowing. -->

## Hard constraints
<!-- Never traded off. Each one is backed by a verify/run.sh step or a hook where
     possible; the spec checks every change against this list. -->
- 

## Verifying your work
- Run `verify/run.sh` before reporting anything done, and paste the output.
- Tests are never skipped, deleted or loosened to get green. If a test fails, fix the
  code, not the test.
- State a measurable target for each task (a test that passes, a status code, a
  screenshot that matches) and show the evidence.
- Before calling a change done, run the `verifier` agent on it.

## Workflow (AI-native SDLC)
Each stage commits an artifact the next one reads, in `intent/<date>-<slug>/`.
1. **Plan:** `/intent <problem | ticket | alert>` → `intent.md`; I accept or reject.
2. **Design:** `/spec intent/<dir>` → `spec.md` (R1… requirements, constraint table,
   concerns); I give go / no-go.
3. **Build:** `/implement intent/<dir>` → plan mode → accepted plan saved as `plan.md` →
   code. Nothing is implemented without an accepted plan. Bugs: `/fix <bug>` (failing
   test first, locked, then fix the code).
4. **Test:** hooks run `verify/run.sh --fast` on every edit and commit; the `verifier`
   agent checks each requirement before done. <evals: `python3 evals/run.py` after
   changing CLAUDE.md or `.claude/`.>
5. **Deploy:** <review: the `reviewer` agent reviews per `REVIEW.md` before a PR;
   `/sweep-pr` drives a PR to green.> The approval gate asks me before pushes to main,
   force pushes, merges, releases and deploys. I merge.
6. **Maintain:** <maintain: `python3 sdlc/check.py` (daily in CI) turns band breaches
   into draft `intent.md` files to triage with `/intent`.> `python3 sdlc/delivery.py`
   shows lead times and rework.
Trivial changes (typos, one-line fixes) skip stages 1–3.

Parallel work: one worktree per independent task (`claude --worktree <name>`), tasks that
touch the same files stay in one session. `.worktreeinclude` lists git-ignored files
worktrees need.

## Things Claude gets wrong here
<!-- When Claude makes the same mistake twice, the correction goes here. -->
