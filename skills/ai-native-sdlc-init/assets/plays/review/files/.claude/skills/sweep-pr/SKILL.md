---
name: sweep-pr
description: Drive one of Claude's PRs to green. Sweep unresolved review comments and failing checks, fix each on the PR branch, push, and repeat until only the owner's approval is left. Never merges.
argument-hint: <PR number or URL (default: the current branch's PR)>
disable-model-invocation: true
---

# /sweep-pr — address review and checks until green

PR: $ARGUMENTS

1. **Load the PR:** `gh pr view <pr> --json number,headRefName,baseRefName,url,reviewDecision`.
   Check out its head branch (never work on the base branch).
2. **Collect what's open:**
   - unresolved review threads:
     `gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved path line comments(first:20){nodes{author{login} body}}}}}}}' -F o=<owner> -F r=<repo> -F n=<number>`
   - failing checks: `gh pr checks <pr>`, then `gh run view <run-id> --log-failed`.
3. **Address each**, smallest first. For a comment you disagree with, reply with the
   reason instead of changing code. For a failing check, find the cause and say whether
   it's a real failure or flaky, with evidence. Run `verify/run.sh` before every push.
4. **Push to the PR branch** and reply on each thread with what changed. Re-check; repeat
   until checks are green and no thread is unresolved, at most 5 rounds.
5. **Stop** with a summary: what was fixed, what was answered instead, anything still
   open. If a reviewer flagged the same mistake twice, propose the CLAUDE.md line. Merging
   is the owner's decision; don't merge.
