#!/usr/bin/env bash
# PreToolUse hook (Bash): steps that ship or can't be undone wait for a human.
# Matching commands return permissionDecision "ask", so the person running the session
# confirms them. Non-interactive runs (claude -p, CI) treat "ask" as deny: fail closed.
# A skill or CLAUDE.md rule is advisory; this gate is deterministic. Tune the list.
input=$(cat)
field() { printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("command","") if sys.argv[1]=="cmd" else d.get("cwd",""))' "$1" 2>/dev/null; }
cmd=$(field cmd); [ -n "$cmd" ] || exit 0
reason=""
gate() { [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "$1" && reason=$2; }
s='[[:space:]]'
gate "git$s+push.*($s--force|$s-f($s|\$))"                 "force push"
gate "git$s+push.*[[:space:]:+](main|master)($s|\$)"        "push to the default branch"
gate "gh$s+(pr$s+merge|release$s+create)"                   "merge or release"
gate "(terraform$s+(apply|destroy)|kubectl$s+(apply|delete)|helm$s+(install|upgrade|uninstall)|npm$s+(publish|run$s+(deploy|release)))" "deploy or publish"
# `git push` or `git push <remote>` (no branch named) while on the default branch.
if [ -z "$reason" ] && printf '%s' "$cmd" | grep -Eq "git$s+push($s+-[^[:space:]]+)*($s+[^-[:space:]][^[:space:]]*)?$s*(\$|[;&|])"; then
  br=$(git -C "$(field cwd)" branch --show-current 2>/dev/null)
  case "$br" in main|master) reason="push from $br" ;; esac
fi
[ -n "$reason" ] || exit 0
python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"Approval gate ("+sys.argv[1]+"): confirm to run it, or decline and the change waits for you."}}))' "$reason"
