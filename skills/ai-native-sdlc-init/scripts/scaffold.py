#!/usr/bin/env python3
"""Copy AI-native SDLC plays into a project without overwriting anything.

    python3 scaffold.py <target-dir> [--plays core,review,ci,evals,maintain]
                        [--name NAME] [--dry-run] [--no-git-hook] [--list]

- Each play is assets/plays/<play>/files/** (copied) plus an optional
  assets/plays/<play>/settings.json (merged into .claude/settings.json).
- `core` is always installed. Existing files are skipped, never replaced.
- Replaces {{PROJECT_NAME}} in copied text files (default: the target folder's name).
- Settings merge only adds: missing keys, missing permission rules, and hook entries
  whose command isn't already registered for that event.
- Sets git core.hooksPath=.githooks if the target is a git repo and it is unset.
- Never touches CLAUDE.md: the caller writes it from assets/CLAUDE-template.md.
Prints one line per file: CREATED / SKIPPED (exists) / MERGED / UNCHANGED.
"""
import argparse, json, os, shutil, stat, subprocess, sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PLAYS = ASSETS / "plays"
ORDER = ["core", "review", "ci", "evals", "maintain"]


def describe(play: str) -> str:
    readme = PLAYS / play / "PLAY.md"
    return readme.read_text().splitlines()[0].lstrip("# ") if readme.exists() else ""


def copy_tree(src_root: Path, target: Path, name: str, dry: bool) -> None:
    for src in sorted(p for p in src_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(src_root)
        dst = target / rel
        if dst.exists():
            print(f"SKIPPED (exists)  {rel}")
            continue
        print(f"CREATED           {rel}")
        if dry:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            dst.write_text(src.read_text().replace("{{PROJECT_NAME}}", name))
        except UnicodeDecodeError:
            shutil.copyfile(src, dst)
        if os.access(src, os.X_OK):
            dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def merge(cur: dict, frag: dict) -> None:
    for key, val in frag.items():
        if key == "hooks":
            hooks = cur.setdefault("hooks", {})
            for event, entries in val.items():
                have = hooks.setdefault(event, [])
                known = {(e.get("matcher"), h.get("command"))
                         for e in have for h in e.get("hooks", [])}
                for e in entries:
                    if any((e.get("matcher"), h.get("command")) not in known for h in e["hooks"]):
                        have.append(e)
        elif isinstance(val, list):
            have = cur.setdefault(key, [])
            have.extend(v for v in val if v not in have)
        elif isinstance(val, dict):
            merge(cur.setdefault(key, {}), val)
        else:
            cur.setdefault(key, val)


def merge_settings(target: Path, plays: list, dry: bool) -> None:
    path = target / ".claude" / "settings.json"
    cur = json.loads(path.read_text()) if path.exists() else {}
    before = json.dumps(cur, sort_keys=True)
    for play in plays:
        frag = PLAYS / play / "settings.json"
        if frag.exists():
            merge(cur, json.loads(frag.read_text()))
    if json.dumps(cur, sort_keys=True) == before:
        print("UNCHANGED         .claude/settings.json")
        return
    print(("MERGED            " if path.exists() else "CREATED           ") + ".claude/settings.json")
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cur, indent=2) + "\n")


def git_hook(target: Path, dry: bool) -> None:
    def git(*a):
        return subprocess.run(["git", "-C", str(target), *a], capture_output=True, text=True)
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        print("NOTE              not a git repo; run `git config core.hooksPath .githooks` after `git init`")
        return
    cur = git("config", "--get", "core.hooksPath").stdout.strip()
    if cur:
        print(f"UNCHANGED         core.hooksPath already set to {cur!r}")
        return
    print("SET               git config core.hooksPath .githooks")
    if not dry:
        git("config", "core.hooksPath", ".githooks")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?")
    ap.add_argument("--plays", default="core", help="comma-separated; core is always included")
    ap.add_argument("--name")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-git-hook", action="store_true")
    ap.add_argument("--list", action="store_true", help="list plays and exit")
    a = ap.parse_args()
    if a.list:
        for p in ORDER:
            print(f"{p:9} {describe(p)}")
        return 0
    if not a.target:
        ap.error("target is required")
    plays = {p.strip() for p in a.plays.split(",") if p.strip()} | {"core"}
    unknown = plays - set(ORDER)
    if unknown:
        print(f"error: unknown play(s): {', '.join(sorted(unknown))}; see --list", file=sys.stderr)
        return 1
    plays = [p for p in ORDER if p in plays]
    target = Path(a.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 1
    name = a.name or target.name
    print(f"PLAYS             {', '.join(plays)}")
    for play in plays:
        copy_tree(PLAYS / play / "files", target, name, a.dry_run)
    merge_settings(target, plays, a.dry_run)
    if not a.no_git_hook:
        git_hook(target, a.dry_run)
    claude_md = target / "CLAUDE.md"
    print("TODO              CLAUDE.md: " + (
        "exists; merge in the sections it lacks from " if claude_md.exists() else "write it from ")
        + str(ASSETS / "CLAUDE-template.md"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
