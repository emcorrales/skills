---
name: triage
description: Turn a production breach, incident or user feedback into the next step of the loop — a /spec change request or an intent.md update — checked against docs/signals.md and intent.md, then stop for the owner's decision.
argument-hint: <what happened: signal, reading, link or report>
disable-model-invocation: true
---

# /triage — close the loop (stage 6)

Report: $ARGUMENTS

1. **Read** `docs/signals.md` (control bands, breach log) and `intent.md`.
2. **Confirm with data.** Check the reading against its source (dashboards, logs, an
   MCP tool, `git log`) instead of trusting the report. If you can't reach the source,
   say so and mark the reading unconfirmed. Ask at most 3 questions, in one message, if
   the signal or impact is unclear.
3. **Classify**, with the evidence:
   - **Inside the band or noise:** no action.
   - **Breach within the current intent:** a fix or improvement. Draft the change
     request as a one-line `/spec <…>` for the owner to run.
   - **The intent itself is wrong or outdated** (new users, a goal or constraint that
     no longer holds): propose the `intent.md` edit as a diff. A changed intent restarts
     planning.
   - **A signal has no band yet:** propose a row for the control-bands table.
   - If the cause was Claude repeating a mistake, propose a line for CLAUDE.md "Things
     Claude gets wrong here".
4. **Log it:** append a row to the breach log in `docs/signals.md`. That is the only file
   you edit; don't touch `intent.md`, specs or code.
5. **Stop.** Show the classification, the evidence and the proposed next step, and ask
   the owner to decide.
