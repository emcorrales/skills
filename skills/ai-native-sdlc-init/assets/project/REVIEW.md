# Review rules — {{PROJECT_NAME}}

Stage 5. Read by the `reviewer` agent and by any AI PR reviewer. Keep it short and
specific to this repo; generic advice belongs nowhere.

## Always check
- The change matches its spec in `docs/specs/` (Requirements and Acceptance), and the
  spec had a `go`.
- No hard constraint from `intent.md` is broken, even ones the spec marked n/a.
- New behavior has a check in `verify/run.sh`, not just a claim in the PR.

## Needs a human reviewer (AI review is not enough)
<!-- Paths or kinds of change that are regulated or critical, e.g.:
- auth/, payments/, migrations/
- anything that touches secrets, PII or permissions -->

## Don't flag
<!-- Style already enforced by the linter, generated files, etc. -->
