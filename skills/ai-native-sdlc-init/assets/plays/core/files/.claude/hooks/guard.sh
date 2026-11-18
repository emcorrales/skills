#!/usr/bin/env bash
# PreToolUse hook (Edit|Write|MultiEdit|NotebookEdit): build-time guardrails.
#  - deny: tests locked by /fix (fix the code, not the test) and generated/frozen paths
#  - ask:  files that define how work is checked or gated, so Claude can't quietly
#          weaken its own checks
# Limits: shell commands that rewrite files bypass this hook; the pre-commit hook,
# CI and review are the backstop. Tune both case lists for the project.
input=$(cat)
path=$(printf '%s' "$input" | python3 -c 'import json,sys; t=json.load(sys.stdin).get("tool_input") or {}; print(t.get("file_path") or t.get("notebook_path") or "")' 2>/dev/null)
[ -n "$path" ] || exit 0
dir=$(dirname "$path"); while [ ! -d "$dir" ]; do dir=$(dirname "$dir"); done
root=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || exit 0
# A private .sdlc/ is its own git repo; the project root is its parent.
case "$root" in */.sdlc) root=${root%/.sdlc} ;; esac
rel=$(python3 -c 'import os,sys; print(os.path.relpath(os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2])))' "$path" "$root")
case "$rel" in ../*) exit 0 ;; esac

decide() {  # decide <allow|ask|deny> <reason>
  python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":sys.argv[1],"permissionDecisionReason":sys.argv[2]}}))' "$1" "$2"
  exit 0
}

lock=$(git -C "$root" rev-parse --git-path claude-locked-tests)
case "$lock" in /*) ;; *) lock="$root/$lock" ;; esac
if [ -f "$lock" ] && grep -Fxq "$rel" "$lock"; then
  decide deny "$rel is locked by /fix: it reproduces the bug. Fix the code, not the test. If the test is wrong, stop and tell the owner."
fi

case "$rel" in
  # Generated or frozen paths, never edited by hand, e.g.:  src/gen/*|vendor/*)
  __none__) decide deny "$rel is generated or frozen. Change its source instead." ;;
esac

case "$rel" in
  verify/*|evals/*|sdlc/bands.json|REVIEW.md|.sdlc/verify/*|.sdlc/evals/*|.sdlc/bands.json|.sdlc/REVIEW.md|\
  .claude/hooks/*|.claude/settings.json|.claude/settings.local.json|.githooks/*|.github/workflows/*)
    decide ask "$rel defines how work is checked or gated. Confirm only if this change is meant to alter the checks." ;;
esac
exit 0
