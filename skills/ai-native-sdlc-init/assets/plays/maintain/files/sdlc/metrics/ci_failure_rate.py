#!/usr/bin/env python3
"""Daily CI failure rate from GitHub Actions, as JSON readings (oldest first).

    python3 sdlc/metrics/ci_failure_rate.py [--days 45] [--workflow verify.yml]

One reading per day that had completed runs: failed / completed. Days without runs are
skipped, not counted as zero. Needs the gh CLI, authenticated.
"""
import argparse, collections, datetime, json, shutil, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=45)
ap.add_argument("--workflow")
a = ap.parse_args()
if not shutil.which("gh"):
    sys.exit("BLOCKED: gh CLI not found (install it and run `gh auth login`)")
cmd = ["gh", "run", "list", "--limit", "1000", "--json", "conclusion,createdAt,status"]
if a.workflow:
    cmd += ["--workflow", a.workflow]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode:
    sys.exit(f"gh run list failed: {r.stderr.strip()}")
since = datetime.date.today() - datetime.timedelta(days=a.days)
days = collections.defaultdict(lambda: [0, 0])
for run in json.loads(r.stdout):
    if run["status"] != "completed" or run["conclusion"] in ("cancelled", "skipped"):
        continue
    day = datetime.date.fromisoformat(run["createdAt"][:10])
    if day >= since:
        days[day][1] += 1
        days[day][0] += run["conclusion"] == "failure"
print(json.dumps([round(f / n, 4) for d, (f, n) in sorted(days.items())]))
