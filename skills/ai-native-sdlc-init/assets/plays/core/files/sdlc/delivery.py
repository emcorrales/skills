#!/usr/bin/env python3
"""Delivery metrics for intent/<change>/ folders, read from git history.

    python3 sdlc/delivery.py [--json]

Per change (the playbook's leading and lagging indicators for stages 1-3):
  intent->spec   hours from the first intent.md commit to the first spec.md commit
  spec->plan     hours from the first spec.md commit to the first plan.md commit
  intent edits   commits to intent.md after spec.md was first committed (intent rework)
  spec edits     commits to spec.md after plan.md was first committed (requirements rework)
Plus repeat corrections: bullets under CLAUDE.md "Things Claude gets wrong".
Only committed files count; uncommitted drafts are ignored.
"""
import json, re, statistics, subprocess, sys
from pathlib import Path


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def commit_times(path: Path):
    return sorted(int(t) for t in git("log", "--format=%ct", "--", str(path)).split())


def status(path: Path):
    m = re.search(r"Status:\s*([a-z ]+?)\s*(?:·|$)", path.read_text(), re.M) if path.exists() else None
    return m.group(1) if m else "-"


def hours(a, b):
    return round((b - a) / 3600, 1) if a and b else None


def main():
    root = Path(git("rev-parse", "--show-toplevel").strip() or ".")
    rows = []
    for d in sorted(p for p in (root / "intent").glob("*/") if p.is_dir()):
        t = {n: commit_times(d / f"{n}.md") for n in ("intent", "spec", "plan")}
        first = {n: (v[0] if v else None) for n, v in t.items()}
        rows.append({
            "change": d.name,
            "intent": status(d / "intent.md"),
            "spec": status(d / "spec.md"),
            "intent->spec h": hours(first["intent"], first["spec"]),
            "spec->plan h": hours(first["spec"], first["plan"]),
            "intent edits after spec": sum(x > first["spec"] for x in t["intent"]) if first["spec"] else None,
            "spec edits after plan": sum(x > first["plan"] for x in t["spec"]) if first["plan"] else None,
        })
    claude_md = root / "CLAUDE.md"
    wrong = 0
    if claude_md.exists():
        m = re.search(r"^## Things Claude gets wrong[^\n]*\n(.*?)(?=^## |\Z)", claude_md.read_text(), re.M | re.S)
        wrong = len(re.findall(r"^\s*[-*] \S", m.group(1), re.M)) if m else 0

    if "--json" in sys.argv:
        print(json.dumps({"changes": rows, "claude_md_corrections": wrong}, indent=2))
        return 0
    if not rows:
        print("No intent/<change>/ folders with history yet.")
    else:
        cols = list(rows[0])
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join("-" if r[c] is None else str(r[c]) for c in cols))
        for c in ("intent->spec h", "spec->plan h"):
            vals = [r[c] for r in rows if r[c] is not None]
            if vals:
                print(f"median {c}: {statistics.median(vals)}")
    print(f"CLAUDE.md 'Things Claude gets wrong' entries: {wrong}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
