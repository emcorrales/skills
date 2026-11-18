## Verify (before calling anything done, and show the output)
```bash
verify/run.sh            # full check
verify/run.sh --fast     # quick subset; run by the post-edit hook and the pre-commit hook
```
Healthy output ends in `VERIFY PASSED`. Enable the pre-commit hook once per clone with
`git config core.hooksPath .githooks`. The `verifier` agent runs the full check from a
fresh context and never edits files.

## Workflow (AI-Native SDLC)
1. **Intent:** goal, constraints and "done" live in `intent.md`. If a change is out of
   scope, update `intent.md` first.
2. **Spec:** `/spec <change>` writes `docs/specs/`, then stops for the owner's go/no-go.
   Skip it for trivial fixes.
3. **Plan:** use plan mode; plans are saved to `docs/plans/`.
4. **Build → `verify/run.sh`:** commit the spec, plan and code together.

For **parallel sessions**, use one worktree each (`claude --worktree <name>`) on tasks that
touch different files. `.worktreeinclude` lists git-ignored files to copy into worktrees.

## Things Claude gets wrong here
<!-- When a review or session surfaces the same correction twice, add it here. -->
