#!/usr/bin/env python3
"""Copy AI-native SDLC plays into a project without overwriting anything.

    python3 scaffold.py <target-dir> [--plays core,review,ci,evals,maintain] [--local]
                        [--name NAME] [--dry-run] [--no-git-hook] [--list]

- Each play is assets/plays/<play>/files/** (copied) plus an optional
  assets/plays/<play>/settings.json (merged into the Claude settings file).
- `core` is always installed. Existing files are skipped, never replaced.
- Replaces {{PROJECT_NAME}} in copied text files (default: the target folder's name).
- Settings merge only adds: missing keys, missing permission rules, and hook entries
  whose command isn't already registered for that event.

Team layout (default): files land at their own paths and are meant to be committed;
settings go to .claude/settings.json; git core.hooksPath=.githooks is set if unset.

--local (private layout): nothing the team can see changes.
- intent/, verify/, sdlc/, evals/, REVIEW.md move under .sdlc/, which gets its own
  private git repo for artifact history. Paths in copied .md/.json text are rewritten.
- settings go to .claude/settings.local.json; the pre-commit hook goes to
  .git/hooks/pre-commit (only if core.hooksPath is unset and no hook exists).
- .github/ workflows are skipped (CI is shared), so the `ci` play isn't available.
- every created path is added to .git/info/exclude, which is never committed.
- CLAUDE.md is the team's; personal workflow notes go to CLAUDE.local.md.
Never touches CLAUDE.md / CLAUDE.local.md: the caller writes it from
assets/CLAUDE-template.md. Prints one line per file: CREATED / SKIPPED (exists) /
MERGED / UNCHANGED / EXCLUDED.
"""
import argparse, json, os, re, shutil, stat, subprocess, sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PLAYS = ASSETS / "plays"
ORDER = ["core", "review", "ci", "evals", "maintain"]
LOCAL_DIRS = ("intent", "verify", "evals")           # -> .sdlc/<dir>/
# Rewrites for prose and config in the private layout. A path is rewritten only where it
# starts a path (not after a word character, '.', '/' or '-').
LOCAL_TEXT = [
    (re.compile(r"(?<![\w./-])(intent|verify|evals)/"), r".sdlc/\1/"),
    (re.compile(r"(?<![\w./-])sdlc/"), ".sdlc/"),
    (re.compile(r"(?<![\w./-])REVIEW\.md"), ".sdlc/REVIEW.md"),
    (re.compile(r"CLAUDE\.md(\s+\"Things)"), r"CLAUDE.local.md\1"),
    (re.compile(r"the CLAUDE\.md line"), "the CLAUDE.local.md line"),
]
EXCLUDE_MARKER = "# ai-native-sdlc-init --local: personal workflow files"
LOCAL_WORKTREEINCLUDE = "\n# Private SDLC layout (untracked, so worktrees need it copied):\n.sdlc/**\n.claude/**\nCLAUDE.local.md\n"


def git(target, *a):
    return subprocess.run(["git", "-C", str(target), *a], capture_output=True, text=True)


def describe(play: str) -> str:
    readme = PLAYS / play / "PLAY.md"
    return readme.read_text().splitlines()[0].lstrip("# ") if readme.exists() else ""


def local_text(s: str) -> str:
    for pat, sub in LOCAL_TEXT:
        s = pat.sub(sub, s)
    return s


def destination(rel: Path, local: bool):
    """Where a play file goes: a repo-relative path, 'PRE-COMMIT', or None to skip."""
    if not local:
        return rel
    parts = rel.parts
    if parts[0] == ".github":
        return None
    if rel == Path(".githooks/pre-commit"):
        return "PRE-COMMIT"
    if parts[0] in LOCAL_DIRS:
        return Path(".sdlc", *parts)
    if parts[0] == "sdlc":
        return Path(".sdlc", *parts[1:])
    if rel == Path("REVIEW.md"):
        return Path(".sdlc/REVIEW.md")
    return rel


def write(src: Path, dst: Path, name: str, local: bool, extra: str = "") -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        text = src.read_text().replace("{{PROJECT_NAME}}", name)
        if local and src.suffix in (".md", ".json"):
            text = local_text(text)
        dst.write_text(text + extra)
    except UnicodeDecodeError:
        shutil.copyfile(src, dst)
    if os.access(src, os.X_OK):
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def copy_tree(src_root: Path, target: Path, name: str, local: bool, dry: bool, created: list) -> None:
    for src in sorted(p for p in src_root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        rel = src.relative_to(src_root)
        dest = destination(rel, local)
        if dest is None:
            print(f"SKIPPED (shared)  {rel}  (CI is shared; not installed in --local)")
            continue
        if dest == "PRE-COMMIT":
            install_pre_commit(src, target, name, dry, created)
            continue
        dst = target / dest
        if dst.exists():
            print(f"SKIPPED (exists)  {dest}")
            continue
        print(f"CREATED           {dest}")
        created.append(dest)
        if not dry:
            extra = LOCAL_WORKTREEINCLUDE if local and rel == Path(".worktreeinclude") else ""
            write(src, dst, name, local, extra)


def install_pre_commit(src: Path, target: Path, name: str, dry: bool, created: list) -> None:
    hooks_path = git(target, "config", "--get", "core.hooksPath").stdout.strip()
    if hooks_path:
        print(f"SKIPPED           pre-commit: core.hooksPath is {hooks_path!r}; call "
              f"{src.name} from that hook yourself if you want it")
        return
    p = git(target, "rev-parse", "--git-path", "hooks/pre-commit").stdout.strip()
    dst = Path(p) if os.path.isabs(p) else target / p
    if dst.exists():
        print(f"SKIPPED (exists)  {dst.relative_to(target) if dst.is_relative_to(target) else dst}")
        return
    print("CREATED           .git/hooks/pre-commit (private; not committed)")
    if not dry:
        write(src, dst, name, False)


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


def merge_settings(target: Path, plays: list, local: bool, dry: bool, created: list) -> None:
    rel = Path(".claude/settings.local.json" if local else ".claude/settings.json")
    path = target / rel
    cur = json.loads(path.read_text()) if path.exists() else {}
    before = json.dumps(cur, sort_keys=True)
    for play in plays:
        frag = PLAYS / play / "settings.json"
        if frag.exists():
            text = frag.read_text()
            merge(cur, json.loads(local_text(text) if local else text))
    if json.dumps(cur, sort_keys=True) == before:
        print(f"UNCHANGED         {rel}")
        return
    print(("MERGED            " if path.exists() else "CREATED           ") + str(rel))
    if not path.exists():
        created.append(rel)
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cur, indent=2) + "\n")


def team_git_hook(target: Path, dry: bool) -> None:
    cur = git(target, "config", "--get", "core.hooksPath").stdout.strip()
    if cur:
        print(f"UNCHANGED         core.hooksPath already set to {cur!r}")
        return
    print("SET               git config core.hooksPath .githooks")
    if not dry:
        git(target, "config", "core.hooksPath", ".githooks")


def exclude(target: Path, created: list, dry: bool) -> None:
    p = git(target, "rev-parse", "--git-common-dir").stdout.strip()
    path = (Path(p) if os.path.isabs(p) else target / p) / "info" / "exclude"
    have = set(path.read_text().splitlines()) if path.exists() else set()
    want = []
    for rel in [".sdlc/", "CLAUDE.local.md", ".claude/settings.local.json"] + [str(r) for r in created]:
        if rel.startswith(".sdlc/") and rel != ".sdlc/":
            continue
        line = "/" + rel
        if line not in have and line not in want:
            want.append(line)
    if not want:
        print("UNCHANGED         .git/info/exclude")
        return
    print(f"EXCLUDED          {len(want)} paths in .git/info/exclude (local to this clone)")
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(f"\n{EXCLUDE_MARKER}\n" + "\n".join(want) + "\n")


def init_private_repo(target: Path, dry: bool) -> None:
    sdlc = target / ".sdlc"
    if (sdlc / ".git").exists():
        print("UNCHANGED         .sdlc/.git (private artifact history)")
        return
    print("CREATED           .sdlc/.git (private artifact history)")
    if dry:
        return
    sdlc.mkdir(exist_ok=True)
    git(sdlc, "init", "-q")
    git(sdlc, "add", "-A")
    r = git(sdlc, "commit", "-q", "--no-verify", "-m", "Set up private AI-native SDLC")
    if r.returncode:
        print("NOTE              .sdlc: initial commit failed (git user.name/email set?); "
              "record.sh will commit later")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?")
    ap.add_argument("--plays", default="core", help="comma-separated; core is always included")
    ap.add_argument("--local", action="store_true", help="private layout: nothing shared changes")
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
    if a.local and "ci" in plays:
        print("error: the ci play only adds shared CI workflows; drop it for --local", file=sys.stderr)
        return 1
    plays = [p for p in ORDER if p in plays]
    target = Path(a.target).resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 1
    is_repo = git(target, "rev-parse", "--is-inside-work-tree").returncode == 0
    if a.local and not is_repo:
        print("error: --local needs a git repo (it hides its files via .git/info/exclude)", file=sys.stderr)
        return 1
    name = a.name or target.name
    created: list = []
    print(f"PLAYS             {', '.join(plays)}  ({'private' if a.local else 'team'} layout)")
    for play in plays:
        copy_tree(PLAYS / play / "files", target, name, a.local, a.dry_run, created)
    merge_settings(target, plays, a.local, a.dry_run, created)
    if a.local:
        exclude(target, created, a.dry_run)
        init_private_repo(target, a.dry_run)
    elif not a.no_git_hook:
        if is_repo:
            team_git_hook(target, a.dry_run)
        else:
            print("NOTE              not a git repo; run `git config core.hooksPath .githooks` after `git init`")
    md = "CLAUDE.local.md" if a.local else "CLAUDE.md"
    print(f"TODO              {md}: " + (
        "exists; merge in the sections it lacks from " if (target / md).exists() else "write it from ")
        + str(ASSETS / "CLAUDE-template.md")
        + (" (workflow sections only; CLAUDE.md is the team's)" if a.local else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
