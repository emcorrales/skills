## Verify (before calling anything done, and show the output)
```bash
verify/run.sh            # full check
verify/run.sh --fast     # quick subset; run by the post-edit hook and the pre-commit hook
```
Healthy output ends in `VERIFY PASSED`. Enable the pre-commit hook once per clone with
`git config core.hooksPath .githooks`. The `verifier` agent runs the full check from a
fresh context and never edits files.

## Workflow (AI-Native SDLC)
Each stage commits an artifact the next one reads; stage 6 feeds back into stage 1.
1. **Plan — intent:** goal, constraints and "done" live in `intent.md`. If a change is
   out of scope, update `intent.md` first.
2. **Design — spec:** `/spec <change>` writes `docs/specs/`, then stops for the owner's
   go/no-go. Skip it for trivial fixes.
3. **Build — plan:** use plan mode; plans are saved to `docs/plans/`. Commit the spec,
   plan and code together.
4. **Test — `verify/run.sh`:** run locally by the hooks and the `verifier` agent, and in
   CI on every PR (`.github/workflows/verify.yml`).
5. **Deploy — review and gate:** run the `reviewer` agent before opening or merging a PR;
   rules are in `REVIEW.md`, including what always needs a human reviewer. The approval
   gate hook makes a human confirm pushes to main, force pushes, merges and deploys.
6. **Maintain — signals:** `docs/signals.md` lists what we watch and its healthy band.
   On a breach, incident or feedback, `/triage <what happened>` proposes the next
   `/spec` or an `intent.md` update.

For **parallel sessions**, use one worktree each (`claude --worktree <name>`) on tasks that
touch different files. `.worktreeinclude` lists git-ignored files to copy into worktrees.

## Things Claude gets wrong here
<!-- When a review or session surfaces the same correction twice, add it here. -->
