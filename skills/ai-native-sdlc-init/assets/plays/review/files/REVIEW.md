# Review instructions — {{PROJECT_NAME}}

Used by the `reviewer` agent and by Claude review on PRs. Tune it monthly: rate past
findings and cut what wasn't useful.

## Passes
Run three passes and tag each finding with its pass:
- **Bugs:** logic errors, edge cases, regressions.
- **Security:** injection, auth gaps, secrets or PII in logs and errors.
- **Compliance:** the diff matches its `spec.md` requirements (R-IDs) and `plan.md`, and
  follows CLAUDE.md conventions and hard constraints. Unplanned scope is a finding.

## What Important means here
Important is for findings that would break behavior, leak data, or breach a policy or
hard constraint. Style and naming are nits.

## Cap the nits
At most five nits per review; summarize the rest as a count.

## Do not report
- Generated files <!-- e.g. src/gen/ -->
- Anything CI or `verify/run.sh` already enforces (formatting, lint rules, types)

## Needs a human
<!-- Paths where AI review never suffices, e.g. auth/, migrations/, billing/ -->
