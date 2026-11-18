---
name: intent
description: Stage 1 (Plan). Turn an idea, ticket or production alert into intent/<date>-<slug>/intent.md by asking analyst questions, then stop for the owner to correct and accept it.
argument-hint: <the problem in your own words, a ticket link, or an alert/breach>
disable-model-invocation: true
---

# /intent — capture intent (stage 1)

Input: $ARGUMENTS

Intent says **what is wanted, why, and under which constraints**. No design, no code.

1. **Listen first.** Take the problem as given: what can't be done today, who is
   affected, what better looks like, what is out of scope. If the input is a ticket or
   alert, read it (link, `gh issue view`, the breach report) and the code it points at.
2. **Ask like an analyst** until it is concrete: scope, affected users and systems,
   constraints, how success will be recognized. One message, at most 4 questions,
   with your best guess drafted for each so the owner can just confirm. Skip questions
   the input already answers.
3. **Write** `intent/<YYYY-MM-DD>-<kebab-slug>/intent.md` from [template.md](template.md),
   Status `draft`. Keep it short; bullets are fine. Constraints include any hard
   constraint from CLAUDE.md that this change touches. If an external ticket exists,
   put its ID on the `Ticket:` line (the ticket should link back to the commit).
4. **Stop.** Show the file and ask the owner to correct anything wrong, then accept or
   reject. On **accept**: set Status `accepted` and record it:
   `sdlc/record.sh "intent: <slug>" intent/<dir>/intent.md`. On **reject**: set Status
   `rejected` and record it anyway (a closed intent is part of the record). Then suggest `/spec intent/<dir>`.
