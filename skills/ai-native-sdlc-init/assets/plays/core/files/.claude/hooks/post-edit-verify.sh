#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|MultiEdit): after Claude edits a file that matters, run
# the fast verify. On failure exit 2, so the output goes back to Claude to fix (a
# PostToolUse hook can't undo the edit). Keep --fast fast: heavy checks belong at
# commit, CI and PR.
path=$(python3 -c 'import json,sys; print((json.load(sys.stdin).get("tool_input") or {}).get("file_path",""))' 2>/dev/null)
[ -n "$path" ] || exit 0
# Edits that never need a verify run. Tune this list for the project.
case "$path" in
  */intent/*|*/docs/*|*.md|*/.claude/*|*/.git/*) exit 0 ;;
esac
# Verify the checkout that contains the edited file (works inside worktrees too).
root=$(git -C "$(dirname "$path")" rev-parse --show-toplevel 2>/dev/null) || root=$CLAUDE_PROJECT_DIR
# A private .sdlc/ is its own git repo; the project root is its parent.
case "$root" in */.sdlc) root=${root%/.sdlc} ;; esac
v="$root/.sdlc/verify/run.sh"; [ -x "$v" ] || v="$root/verify/run.sh"   # private or team layout
[ -x "$v" ] || exit 0
out=$(cd "$root" && "$v" --fast 2>&1) && exit 0
{ echo "Fast verify failed after editing $path:"; echo "$out"; } >&2
exit 2
