#!/usr/bin/env bash
# The feedback loop: one command for "is it done?". Exit 0 and a last line of
# VERIFY PASSED means healthy.
#   verify/run.sh          full check (everything, including slow steps)
#   verify/run.sh --fast   quick subset for the post-edit and pre-commit hooks (aim for ~1s)
# Back each hard constraint in CLAUDE.md with a step where possible. A step that can't
# run (missing tool) must print BLOCKED and fail, never silently pass.
set -u
# Run against the checkout you're in (a worktree, an eval scratch copy), not the one this
# script lives in. A private .sdlc/ is its own repo, so step out of it.
top=$(git rev-parse --show-toplevel 2>/dev/null) || top=$(cd "$(dirname "$0")/.." && pwd)
case "$top" in */.sdlc) top=${top%/.sdlc} ;; esac
cd "$top"
fast=0; [ "${1:-}" = "--fast" ] && fast=1
fail=0; ran=0

step() {  # step <label> <command...>
  local label=$1; shift; ran=$((ran+1))
  if out=$("$@" 2>&1); then echo "PASS  $label"
  else echo "FAIL  $label"; echo "$out" | sed 's/^/      /'; fail=1; fi
}

# ---- fast steps (run always) ------------------------------------------------
# step "lint"        npm run -s lint
# step "unit tests"  python3 -m pytest -q

# ---- slow steps (full run only) ---------------------------------------------
if [ $fast -eq 0 ]; then
  :
  # step "e2e"       npm run -s e2e
fi

[ $ran -eq 0 ] && echo "WARNING: no checks configured yet; edit verify/run.sh"
if [ $fail -eq 0 ]; then echo "VERIFY PASSED"; else echo "VERIFY FAILED"; exit 1; fi
