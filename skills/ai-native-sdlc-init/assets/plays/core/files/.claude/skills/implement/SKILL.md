---
name: implement
description: Stage 3 (Build). From an approved spec.md, plan in plan mode, record the accepted plan as plan.md, then implement it against the feedback loop and hand off to the verifier.
argument-hint: <intent/<dir> (default: newest approved spec without a plan)>
disable-model-invocation: true
---

# /implement — plan mode, then build (stage 3)

Change: $ARGUMENTS

**Nothing is implemented without an accepted plan.**

1. **Check the inputs.** `spec.md` must be Status `approved`; if not, stop.
2. **Plan in plan mode.** Enter plan mode (call EnterPlanMode if you have it; otherwise
   ask the owner to switch with Shift+Tab and wait). Read `intent.md`, `spec.md`,
   CLAUDE.md and the code. Draft a plan with the sections of
   [plan-template.md](plan-template.md): files that change, order of work (each step
   cites R-IDs), risks (cite the spec's concerns) and proof (the test or check that
   proves each requirement).
3. **Interrogate it before presenting:** what could break, which step is riskiest, which
   options you didn't take and why. Put the answers in Risks. The bar: an engineer who
   never saw this conversation could implement from the plan alone.
4. **Get it accepted** (ExitPlanMode). Iterate on feedback until the owner accepts.
5. **Record it first.** Before touching code, write the accepted plan to `plan.md` next
   to the spec, with the date.
6. **Implement** in the planned order, running `verify/run.sh --fast` as you go (the
   post-edit hook does this too). New behavior gets the test named in Proof. When the
   work departs from the plan, update `plan.md` in the same commit as the change.
7. **Done means proven:** run `verify/run.sh` and paste the output, then run the
   `verifier` agent on this change folder. Fix what it reports and re-run it.
8. **Hand off.** Summarize the work, cited by R-ID, and offer to commit `plan.md` and the
   code together (`feat: <slug>` or `fix: <slug>`). Don't push or merge.
