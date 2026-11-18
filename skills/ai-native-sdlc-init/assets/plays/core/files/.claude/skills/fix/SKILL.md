---
name: fix
description: Fix a bug test-first. Reproduce it as a failing test, confirm it fails for the expected reason, commit and lock the test, then fix the code (never the test) until verify passes.
argument-hint: <the bug: symptom, report or issue link>
disable-model-invocation: true
---

# /fix — reproduce, lock, fix (feedback loop)

Bug: $ARGUMENTS

1. **Reproduce as a test.** Find the smallest test that shows the bug. Run it and
   confirm it fails **for the expected reason** (quote the failure). A test that fails
   for another reason, or passes, doesn't count yet.
2. **Commit the test alone:** `git commit --no-verify -m "test: reproduce <bug>"`
   (`--no-verify` because the pre-commit verify would reject a red test; this is the only
   place that's allowed).
3. **Lock it:** `echo "<repo-relative test path>" >> "$(git rev-parse --git-path claude-locked-tests)"`.
   The guard hook now denies edits to that file.
4. **Fix the code, not the test.** Iterate until the test passes, then run
   `verify/run.sh` and paste the output. If you believe the test itself is wrong, stop
   and say why; don't unlock it yourself.
5. **Unlock** (remove the line from the lock file), offer to commit the fix
   (`fix: <bug>`), and if the same kind of mistake has happened before, propose a line for
   CLAUDE.md "Things Claude gets wrong here".
