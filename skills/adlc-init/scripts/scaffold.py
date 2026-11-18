#!/usr/bin/env python3
"""Copy the ADLC scaffold into a project without overwriting anything.

    python3 scaffold.py <target-dir> [--name NAME] [--dry-run] [--no-git-hook]

- Copies assets/project/** into the target. Existing files are skipped, never replaced.
- Replaces {{PROJECT_NAME}} in copied files (default: the target folder's name).
- Merges assets/settings-fragment.json into .claude/settings.json: adds plansDirectory,
  worktree.baseRef and the PostToolUse hook only if they are missing.
- Sets git core.hooksPath=.githooks if the target is a git repo and it is unset.
- Never touches CLAUDE.md: the caller merges assets/CLAUDE-workflow.md by hand.
Prints one line per file: CREATED / SKIPPED (exists) / MERGED / UNCHANGED.
"""
import argparse, json, os, shutil, stat, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "assets"
HOOK_CMD_MARK = "post-edit-verify.sh"


def copy_tree(target: Path, name: str, dry: bool) -> None:
    src_root = HERE / "project"
    for src in sorted(p for p in src_root.rglob("*") if p.is_file()):
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


def merge_settings(target: Path, dry: bool) -> None:
    frag = json.loads((HERE / "settings-fragment.json").read_text())
    path = target / ".claude" / "settings.json"
    cur = json.loads(path.read_text()) if path.exists() else {}
    before = json.dumps(cur, sort_keys=True)
    cur.setdefault("plansDirectory", frag["plansDirectory"])
    cur.setdefault("worktree", {}).setdefault("baseRef", frag["worktree"]["baseRef"])
    post = cur.setdefault("hooks", {}).setdefault("PostToolUse", [])
    if HOOK_CMD_MARK not in json.dumps(post):
        post.extend(frag["hooks"]["PostToolUse"])
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
    ap.add_argument("target")
    ap.add_argument("--name")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-git-hook", action="store_true")
    a = ap.parse_args()
    target = Path(a.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 1
    name = a.name or target.name
    copy_tree(target, name, a.dry_run)
    merge_settings(target, a.dry_run)
    if not a.no_git_hook:
        git_hook(target, a.dry_run)
    claude_md = target / "CLAUDE.md"
    has = claude_md.exists() and "## Workflow" in claude_md.read_text()
    print("TODO              CLAUDE.md: " + ("workflow section present; review it" if has
          else f"merge {HERE / 'CLAUDE-workflow.md'}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
