#!/usr/bin/env python3
"""Deterministic control-band detection. No model involved; unit-tested.

    echo '[0.1, 0.2, ...]' | python3 sdlc/detect.py [--direction up|down]
                                                   [--min-baseline 24] [--sigma-floor 0.01]

Input: a JSON list of readings (or {"readings": [...]}), oldest first, newest last.
Baseline: mean and standard deviation of every reading before the last 8 (the last 8
are the window the drift rules look at). A sigma floor stops a flat baseline from
turning noise into a breach.
Tiers, from the newest reading's distance from the mean in sigmas: 1sigma, 2sigma,
3sigma. Western Electric drift rules count as 2sigma: four of the last five readings
beyond 1 sigma, or eight in a row on the bad side of the mean.
Output: JSON {"tier", "rule", "reading", "mean", "sigma", "z"}; tier is "none" when
within band. Exit 2 if there isn't enough baseline.
"""
import argparse, json, statistics, sys

WINDOW = 8
TIERS = ["none", "1sigma", "2sigma", "3sigma"]


def detect(readings, direction="up", min_baseline=24, sigma_floor=0.01):
    if len(readings) < min_baseline + WINDOW:
        raise ValueError(f"need at least {min_baseline + WINDOW} readings, got {len(readings)}")
    base = readings[:-WINDOW]
    mean = statistics.fmean(base)
    sigma = max(statistics.pstdev(base), sigma_floor)
    sign = 1 if direction == "up" else -1
    z = [sign * (x - mean) / sigma for x in readings[-WINDOW:]]
    now = z[-1]
    level = 3 if now >= 3 else 2 if now >= 2 else 1 if now >= 1 else 0
    rule = f"latest at {now:.1f} sigma" if level else None
    if level < 2 and sum(v > 1 for v in z[-5:]) >= 4:
        level, rule = 2, "drift: 4 of last 5 beyond 1 sigma"
    if level < 2 and all(v > 0 for v in z):
        level, rule = 2, f"drift: {WINDOW} in a row beyond the mean"
    return {"tier": TIERS[level], "rule": rule, "reading": readings[-1],
            "mean": round(mean, 6), "sigma": round(sigma, 6), "z": round(now, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--direction", choices=["up", "down"], default="up",
                    help="which way is bad (up: higher is worse)")
    ap.add_argument("--min-baseline", type=int, default=24)
    ap.add_argument("--sigma-floor", type=float, default=0.01)
    a = ap.parse_args()
    data = json.load(sys.stdin)
    readings = [float(x) for x in (data["readings"] if isinstance(data, dict) else data)]
    try:
        print(json.dumps(detect(readings, a.direction, a.min_baseline, a.sigma_floor)))
    except ValueError as e:
        print(json.dumps({"tier": "none", "error": str(e)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
