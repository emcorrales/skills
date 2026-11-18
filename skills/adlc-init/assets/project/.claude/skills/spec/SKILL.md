---
name: spec
description: Turn a change request into a short spec (docs/specs/<date>-<slug>.md) checked against intent.md and the project's hard constraints, with concerns flagged, then stop for the owner's go/no-go. Use before planning or building any non-trivial change.
argument-hint: <what you want to change, in your own words>
disable-model-invocation: true
---

# /spec — requirements & design step (stage 2)

Change request: $ARGUMENTS

Produce a **short** spec for this change. Nobody writes code in this step.

1. **Read first:** `intent.md` (goal, constraints, "Done when", out of scope) and
   `CLAUDE.md` ("Hard constraints", "Things Claude gets wrong here"). Check facts against
   the code or the project's sources of truth; don't work from memory.
2. **Ask before writing** if scope, the affected deliverable, or what "done" means is
   unclear. Ask at most 3 questions, in one message.
3. **Write** `docs/specs/<YYYY-MM-DD>-<kebab-slug>.md` from [template.md](template.md).
   Keep it under about a page. In the constraints table, check **every** hard constraint
   and give each one a status: ✅ satisfied, ⚠️ concern, or n/a.
4. **Flag concerns**, especially where the change conflicts with `intent.md` or a hard
   constraint, or where two constraints pull against each other. If the change is outside
   the scope of `intent.md`, say that `intent.md` must be updated first: a changed intent
   restarts planning.
5. **Acceptance** must be checkable. Map each item to a step of `verify/run.sh` or to a
   specific new check that should be added to it.
6. **Stop.** Show the spec path and the flagged concerns, and ask the owner for
   **go / no-go**. Don't enter plan mode or edit code until they say go. After go, plan
   in plan mode; the plan is saved to `docs/plans/`. Add the plan's filename to the
   spec's `Plan:` line, and commit the spec, plan and code together.
