#!/usr/bin/env python3
"""Close the loop: check each control band and turn breaches into the next intent.md.

    python3 sdlc/check.py [--metric NAME] [--dry-run]

For each band in sdlc/bands.json: run its `source` command (prints a JSON list of
readings, oldest first), run the deterministic detector, then act by tier:
  1sigma  log only
  2sigma  Claude diagnoses read-only (the tier's `tools`) and writes its finding as
          intent/<date>-breach-<metric>/intent.md (Status: draft) for you to triage
  3sigma  same, but Claude may also act through the tier's pre-approved `routes`
          (e.g. a draft PR into review, a runbook command). Never anything else.
Detection never involves a model. Claude runs stateless (`claude -p`) and gets only the
tools the tier allows; the approval gate hook still applies and fails closed.
Triage the drafts with /intent: accept (fix now or schedule) or reject (dismissals are a
signal to tune the band). When a fix ships, add an eval for the incident.
--dry-run detects and prints, without calling Claude or writing files.
"""
import argparse, datetime, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect import detect  # noqa: E402

HERE = Path(__file__).resolve().parent      # sdlc/ (team) or .sdlc/ (private)
ROOT = HERE.parent
INTENT = (HERE if HERE.name == ".sdlc" else ROOT) / "intent"
LEVEL = {"none": 0, "1sigma": 1, "2sigma": 2, "3sigma": 3}


def act_tier(band, tier):
    """The highest configured tier at or below the detected one."""
    tiers = band.get("tiers", {})
    for t in sorted(tiers, key=LEVEL.get, reverse=True):
        if LEVEL[t] <= LEVEL[tier]:
            return t, tiers[t]
    return None, None


def prompt_for(band, det, readings, cfg):
    template = ROOT / ".claude/skills/intent/template.md"
    routes = cfg.get("routes", [])
    return f"""A production control band was breached in this repository. You run unattended.

Metric: {band['metric']} ({band.get('description', '')})
Detection (deterministic): {json.dumps(det)}
Recent readings, oldest first: {json.dumps(readings[-16:])}

1. Diagnose the likely cause from the code, git history and the read-only tools you have.
   Cite evidence (commits, files, run IDs). Say what you could not check.
2. {"You may act ONLY through these pre-approved routes, and only if the evidence supports it: " + "; ".join(routes) + ". Never push to main, merge, or deploy." if routes else "Do not change anything: diagnosis only."}
3. Your final answer is ONLY the markdown of an intent.md in this format, Status: draft,
   Author: claude (sdlc/check.py). Put the anomaly and evidence under Problem, add a
   section "## Action already taken" (or "none"), and list open questions for the owner.

Format:
{template.read_text() if template.exists() else "# Intent / Problem / Proposed outcome / Affected users and systems / Constraints / Open questions"}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    bands = json.loads((HERE / "bands.json").read_text())["bands"]
    worst = 0
    for band in bands:
        if a.metric and band["metric"] != a.metric:
            continue
        name = band["metric"]
        src = subprocess.run(band["source"], shell=True, cwd=ROOT, capture_output=True, text=True)
        if src.returncode:
            print(f"BLOCKED {name}: source failed: {src.stderr.strip()[:300]}")
            worst = max(worst, 1)
            continue
        readings = [float(x) for x in json.loads(src.stdout or "[]")]
        try:
            det = detect(readings, band.get("direction", "up"), band.get("min_baseline", 24),
                         band.get("sigma_floor", 0.01))
        except ValueError as e:
            print(f"SKIP    {name}: {e}")
            continue
        tier, cfg = act_tier(band, det["tier"])
        print(f"{det['tier'].upper():7} {name}: reading {det['reading']} (mean {det['mean']}, "
              f"sigma {det['sigma']}, z {det['z']}){' - ' + det['rule'] if det['rule'] else ''}")
        if not cfg or cfg.get("action") == "log" or a.dry_run:
            continue
        today = datetime.date.today().isoformat()
        out_dir = INTENT / f"{today}-breach-{name}"
        if out_dir.exists():
            print(f"        {out_dir.relative_to(ROOT)} already exists; not diagnosing again today")
            continue
        r = subprocess.run(["claude", "-p", prompt_for(band, det, readings, cfg),
                            "--allowedTools", cfg.get("tools", "Read,Grep,Glob"),
                            "--output-format", "json"],
                           cwd=ROOT, capture_output=True, text=True, timeout=cfg.get("timeout", 900))
        try:
            text = json.loads(r.stdout).get("result", "").strip()
        except json.JSONDecodeError:
            text = ""
        if not text:
            print(f"FAIL    {name}: Claude returned nothing: {r.stderr.strip()[:300]}")
            worst = max(worst, 1)
            continue
        out_dir.mkdir(parents=True)
        (out_dir / "intent.md").write_text(text + "\n")
        print(f"        wrote {out_dir.relative_to(ROOT)}/intent.md for triage")
    return worst


if __name__ == "__main__":
    sys.exit(main())
