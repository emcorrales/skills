# Signals — {{PROJECT_NAME}}

Stage 6. What we watch once the work is in use, and the band that counts as healthy.
A reading outside its band is a breach: run `/triage <what happened>`, which turns it
into the next spec or an `intent.md` update. That closes the loop back to stage 1.

## Control bands
| Signal | Source (dashboard, query, log) | Healthy band | Owner |
|---|---|---|---|
| <!-- e.g. p95 latency of /search --> | | <!-- < 300 ms --> | |

## Delivery indicators (from git history)
- Lead time: spec date in `docs/specs/` → merge of its code.
- Rework: follow-up fixes to a change within 14 days of merge.
- Repeat corrections: entries added to CLAUDE.md "Things Claude gets wrong here".

## Breach log
| Date | Signal | Reading | Outcome (spec / intent update / no action) |
|---|---|---|---|
