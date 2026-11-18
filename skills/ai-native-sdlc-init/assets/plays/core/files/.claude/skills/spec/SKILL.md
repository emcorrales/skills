---
name: spec
description: Stage 2 (Design). Turn an accepted intent.md into spec.md beside it — numbered requirements, design, how each constraint is met, carried-forward questions and areas of concern — then stop for the owner's go/no-go.
argument-hint: <intent/<dir> (default: newest accepted intent without a spec)>
disable-model-invocation: true
---

# /spec — requirements and design (stage 2)

Change: $ARGUMENTS

Nobody writes code in this step.

1. **Read** the change's `intent.md` (it must be Status `accepted`; if not, stop and
   say so), `CLAUDE.md` (Hard constraints, Architecture, Things Claude gets wrong) and
   the code the change touches. Check facts against the code, not memory.
2. **Apply the project's skills.** List the skills in `.claude/skills/` (and any plugin
   skills) whose policy applies (security, API, UI, data, brand…) and follow them. Name
   them on the `Skills applied:` line.
3. **Write** `spec.md` next to `intent.md` from [template.md](template.md), Status
   `ready for review`. Under about a page.
   - Requirements are numbered **R1, R2, …** so the plan, tests and review can cite them.
     Each one is checkable.
   - Every constraint in the intent and every CLAUDE.md hard constraint the change touches
     gets a row in the constraint table.
   - Carry forward the intent's open questions, answered or not.
   - **Describe clearly any areas of concern, especially where you cannot satisfy
     contradicting policies**, and name who decides each.
4. If the intent itself turns out wrong or incomplete, stop and say so: the fix is to
   amend `intent.md` (a changed intent restarts design), not to paper over it here.
5. **Stop** for the owner's **go / no-go**. Don't plan or edit code. On **go**: set Status
   `approved`, record it (`sdlc/record.sh "spec: <slug>" intent/<dir>/spec.md`), and
   suggest `/implement intent/<dir>`. On **no-go**: set Status `rejected` and record it.
