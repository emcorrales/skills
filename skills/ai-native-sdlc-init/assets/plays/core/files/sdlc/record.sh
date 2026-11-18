#!/usr/bin/env bash
# Record workflow artifacts (intent.md, spec.md, plan.md) in their history.
#   sdlc/record.sh "<message>" <path>...
# Team layout (sdlc/ in the repo): a normal commit of just those paths.
# Private layout (.sdlc/): a commit in .sdlc's own git repo, invisible to the project.
# --no-verify: artifact-only commits don't need the code's fast verify.
set -eu
[ $# -ge 2 ] || { echo "usage: $0 <message> <path>..." >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
msg=$1; shift
abs=(); for p in "$@"; do abs+=("$(cd "$(dirname "$p")" && pwd)/$(basename "$p")"); done
if [ "$(basename "$here")" = .sdlc ]; then
  repo=$here
  [ -d "$repo/.git" ] || git -C "$repo" init -q
else
  repo=$(git -C "$here" rev-parse --show-toplevel)
fi
git -C "$repo" add -- "${abs[@]}"
git -C "$repo" commit -q --no-verify -m "$msg" -- "${abs[@]}"
git -C "$repo" log --oneline -1
