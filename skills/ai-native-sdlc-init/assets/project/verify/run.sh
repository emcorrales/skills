#!/usr/bin/env bash
# One command for "is it done?". Exit 0 and a last line of VERIFY PASSED means healthy.
#   verify/run.sh          full check (everything, including slow steps)
#   verify/run.sh --fast   quick subset for the post-edit and pre-commit hooks (aim for ~1s)
# Add a step per hard constraint in intent.md. A step that can't run (missing tool)
# should print BLOCKED and fail, never silently pass.
set -u
cd "$(dirname "$0")/.."
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
