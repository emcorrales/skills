#!/usr/bin/env python3
"""Switch an installed AI-native SDLC between the team and private (--local) layouts.

    python3 switch.py <target> --to shared|private [--import-history] [--dry-run]

private -> shared (adopting it with the team):
  - moves .sdlc/* to intent/, verify/, evals/, sdlc/, REVIEW.md, rewriting paths in .md/.json
  - moves the workflow's settings entries from settings.local.json to settings.json
  - un-hides the workflow's .claude/ files (removes the .git/info/exclude block)
  - pre-commit: .git/hooks/pre-commit -> .githooks/pre-commit + core.hooksPath
  - stages everything for you to review and commit; nothing is committed, except with
    --import-history, which first replays .sdlc's intent/ history as commits on the
    current branch (author and dates kept, so delivery metrics survive)
  - parks .sdlc/.git at .git/sdlc-private-history.git
private <- shared (keeping it to yourself):
  - moves those paths into .sdlc/ (a new private git repo) and stages their removal
  - stops tracking the workflow's .claude/ files (kept on disk, hidden via exclude)
  - moves settings entries to settings.local.json; pre-commit to .git/hooks
  - stages removal of the workflow's GitHub workflows (they'd break without verify/)
  - --import-history replays the project's intent/ history into .sdlc's repo
  - nothing is committed in the project: the staged removals are yours to commit
CLAUDE.md / CLAUDE.local.md are never edited: the script prints what to move.
Refuses to start if a destination already exists, or the layout is mixed or unknown.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scaffold as sc  # noqa: E402

HOOK_SCRIPTS = ("approval-gate.sh", "guard.sh", "post-edit-verify.sh")
TO_SHARED_TEXT = [
    (re.compile(r"(?<![\w/-])\.sdlc/(intent|verify|evals)/"), r"\1/"),
    (re.compile(r"(?<![\w/-])\.sdlc/REVIEW\.md"), "REVIEW.md"),
    (re.compile(r"(?<![\w/-])\.sdlc/"), "sdlc/"),
    (re.compile(r"CLAUDE\.local\.md(\s+\"Things)"), r"CLAUDE.md\1"),
    (re.compile(r"the CLAUDE\.local\.md line"), "the CLAUDE.md line"),
]
PERSONAL_EXCLUDES = ["/CLAUDE.local.md", "/.claude/settings.local.json"]


def to_shared_text(s):
    for pat, sub in TO_SHARED_TEXT:
        s = pat.sub(sub, s)
    return s


class Switch:
    def __init__(self, target: Path, dry: bool):
        self.t, self.dry, self.todo = target, dry, []

    # ---- helpers -------------------------------------------------------------
    def git(self, *a, cwd=None, env=None, check=True):
        r = subprocess.run(["git", "-C", str(cwd or self.t), *a], capture_output=True, text=True,
                           env={**os.environ, **(env or {})})
        if check and r.returncode:
            raise SystemExit(f"error: git {' '.join(a)}: {r.stderr.strip()}")
        return r.stdout

    def say(self, verb, what):
        print(f"{verb:<17} {what}")

    def tracked(self, rel):
        return bool(self.git("ls-files", "--", str(rel)).strip())

    def git_path(self, p):
        out = self.git("rev-parse", "--git-path", p).strip()
        return Path(out) if os.path.isabs(out) else self.t / out

    def exclude_file(self):
        out = self.git("rev-parse", "--git-common-dir").strip()
        return (Path(out) if os.path.isabs(out) else self.t / out) / "info" / "exclude"

    @staticmethod
    def head(path: Path, n=3):
        try:
            lines = [l for l in path.read_text().splitlines() if l.strip() and not l.startswith("#!")]
        except (UnicodeDecodeError, FileNotFoundError):
            return None
        return [to_shared_text(l) for l in lines[:n]]

    def ours(self, path: Path, asset_rel: str):
        """True if `path` was installed by a play: its first lines match the asset's, with
        {{PROJECT_NAME}} as a wildcard and paths compared in the shared layout."""
        for play in sc.ORDER:
            a = sc.PLAYS / play / "files" / asset_rel
            if a.exists():
                mine, theirs = self.head(path), self.head(a)
                if mine is None or theirs is None or len(mine) != len(theirs):
                    return False
                return all(re.fullmatch(re.escape(t).replace(re.escape("{{PROJECT_NAME}}"), ".*"), m)
                           for m, t in zip(mine, theirs))
        return False

    def workflow_claude_files(self):
        rels = sorted({str(p.relative_to(sc.PLAYS / play / "files"))
                       for play in sc.ORDER
                       for p in (sc.PLAYS / play / "files" / ".claude").rglob("*") if p.is_file()})
        return [r for r in rels if (self.t / r).exists() and self.ours(self.t / r, r)]

    def rewrite_file(self, path: Path, fn):
        if path.suffix in (".md", ".json"):
            text = path.read_text()
            new = fn(text)
            if new != text and not self.dry:
                path.write_text(new)

    def move(self, src: Path, dst: Path, fn):
        """Move a file or tree, rewriting .md/.json text with fn."""
        files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file()
                                                    and ".git" not in p.relative_to(src).parts)
        for f in files:
            d = dst if src.is_file() else dst / f.relative_to(src)
            if not self.dry:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(d))
                self.rewrite_file(d, fn)
        if not self.dry and src.is_dir():
            for d in sorted((p for p in src.rglob("*") if p.is_dir() and ".git" not in p.parts),
                            key=lambda p: len(p.parts), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
            if src.exists() and not any(src.iterdir()):
                src.rmdir()

    def our_perms(self):
        perms = set()
        for play in sc.ORDER:
            f = sc.PLAYS / play / "settings.json"
            if f.exists():
                for text in (f.read_text(), sc.local_text(f.read_text())):
                    perms |= set(json.loads(text).get("permissions", {}).get("allow", []))
        return perms

    def split_settings(self, data):
        """Remove the workflow's entries from settings data; return them as a fragment."""
        frag = {}
        perms = self.our_perms()
        allow = data.get("permissions", {}).get("allow", [])
        mine = [p for p in allow if p in perms]
        if mine:
            data["permissions"]["allow"] = [p for p in allow if p not in perms]
            frag["permissions"] = {"allow": mine}
            if not data["permissions"]["allow"]:
                del data["permissions"]["allow"]
            if not data["permissions"]:
                del data["permissions"]
        for event, entries in list(data.get("hooks", {}).items()):
            keep, move = [], []
            for e in entries:
                cmds = " ".join(h.get("command", "") for h in e.get("hooks", []))
                (move if any(s in cmds for s in HOOK_SCRIPTS) else keep).append(e)
            if move:
                frag.setdefault("hooks", {})[event] = move
                if keep:
                    data["hooks"][event] = keep
                else:
                    del data["hooks"][event]
        if "hooks" in data and not data["hooks"]:
            del data["hooks"]
        return frag

    def move_settings(self, src_rel, dst_rel, fn):
        src, dst = self.t / src_rel, self.t / dst_rel
        if not src.exists():
            return
        data = json.loads(src.read_text())
        frag = json.loads(fn(json.dumps(self.split_settings(data))))
        wt = data.get("worktree", {})
        if wt.get("baseRef") == "head":
            frag["worktree"] = {"baseRef": "head"}
            del wt["baseRef"]
            if not wt:
                del data["worktree"]
        if not frag:
            return
        cur = json.loads(dst.read_text()) if dst.exists() else {}
        sc.merge(cur, frag)
        self.say("MOVED", f"workflow settings {src_rel} -> {dst_rel}")
        if self.dry:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(cur, indent=2) + "\n")
        if data:
            src.write_text(json.dumps(data, indent=2) + "\n")
        else:
            src.unlink()
            self.say("REMOVED", f"{src_rel} (now empty)")

    def replay(self, src_repo: Path, src_prefix: str, dst_repo: Path, dst_prefix: str, fn):
        """Replay commits touching src_prefix/intent as commits in dst_repo, keeping dates."""
        log = self.git("log", "--reverse", "--format=%H%x00%an%x00%ae%x00%aI%x00%cI%x00%s",
                       "--", f"{src_prefix}intent", cwd=src_repo)
        n = 0
        for line in filter(None, log.splitlines()):
            sha, an, ae, ad, cd, subj = line.split("\x00")
            changes = self.git("diff-tree", "--no-commit-id", "--name-status", "-r", "--root", sha,
                               "--", f"{src_prefix}intent", cwd=src_repo)
            paths = []
            for ch in filter(None, changes.splitlines()):
                status, path = ch.split("\t")[0], ch.split("\t")[-1]
                rel = dst_prefix + path[len(src_prefix):]
                dst = dst_repo / rel
                if status.startswith("D"):
                    if not self.dry and dst.exists():
                        dst.unlink()
                else:
                    if not self.dry:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_text(fn(self.git("show", f"{sha}:{path}", cwd=src_repo))
                                       if dst.suffix in (".md", ".json")
                                       else self.git("show", f"{sha}:{path}", cwd=src_repo))
                paths.append(rel)
            if not paths:
                continue
            n += 1
            if self.dry:
                continue
            self.git("add", "-A", "--", *paths, cwd=dst_repo)
            self.git("commit", "-q", "--no-verify", "-m", subj, "--", *paths, cwd=dst_repo,
                     env={"GIT_AUTHOR_NAME": an, "GIT_AUTHOR_EMAIL": ae, "GIT_AUTHOR_DATE": ad,
                          "GIT_COMMITTER_DATE": cd})
        self.say("REPLAYED", f"{n} artifact commits into {'the project' if dst_repo == self.t else '.sdlc history'}")

    # ---- layout detection ----------------------------------------------------
    def layout(self):
        private = (self.t / ".sdlc/verify/run.sh").exists() or (self.t / ".sdlc/intent").is_dir()
        shared = (self.t / "verify/run.sh").exists() and self.ours(self.t / "verify/run.sh", "verify/run.sh") \
            or (self.t / "intent/README.md").exists() and self.ours(self.t / "intent/README.md", "intent/README.md")
        if private and shared:
            raise SystemExit("error: both layouts are present (.sdlc/ and shared paths); resolve by hand first")
        return "private" if private else "shared" if shared else None

    # ---- private -> shared ---------------------------------------------------
    def to_shared(self, history: bool):
        sdlc = self.t / ".sdlc"
        plays = [p for p, f in (("evals", "evals/run.py"), ("maintain", "check.py")) if (sdlc / f).exists()]
        moves = []
        for p in sorted(sdlc.iterdir()):
            if p.name == ".git":
                continue
            rel = p.relative_to(sdlc)
            dest = Path(p.name) if p.name in sc.LOCAL_DIRS or p.name == "REVIEW.md" else Path("sdlc") / rel
            moves.append((p, dest))
        clash = [str(d) for _, d in moves if (self.t / d).exists() and not (self.t / d).is_dir()]
        clash += [str(d) for s, d in moves if s.is_dir() and (self.t / d).is_dir()
                  and any((self.t / d / f.relative_to(s)).exists() for f in s.rglob("*") if f.is_file())]
        if clash:
            raise SystemExit("error: destinations already exist: " + ", ".join(sorted(set(clash))))
        if history:
            if self.git("diff", "--cached", "--name-only").strip():
                raise SystemExit("error: --import-history needs an empty index (commit or unstage first)")
            if (sdlc / ".git").exists():
                self.replay(sdlc, "", self.t, "", to_shared_text)
        staged = []
        for src, dest in moves:
            self.say("MOVED", f".sdlc/{src.relative_to(sdlc)} -> {dest}")
            self.move(src, self.t / dest, to_shared_text)
            staged.append(str(dest))
        claude_files = self.workflow_claude_files()
        for r in claude_files:
            self.rewrite_file(self.t / r, to_shared_text)
        self.move_settings(".claude/settings.local.json", ".claude/settings.json", to_shared_text)
        staged += claude_files + [".claude/settings.json"]
        self.unexclude()
        wti = self.t / ".worktreeinclude"
        if wti.exists() and self.ours(wti, ".worktreeinclude"):
            if not self.dry:
                wti.write_text(wti.read_text().replace(sc.LOCAL_WORKTREEINCLUDE, ""))
            staged.append(".worktreeinclude")
        self.precommit_to_shared(staged)
        if (sdlc / ".git").exists():
            park = self.git_path("sdlc-private-history.git")
            while park.exists():
                park = park.with_name(park.name + "~")
            self.say("PARKED", f".sdlc/.git -> {park.relative_to(self.t) if park.is_relative_to(self.t) else park}")
            if not self.dry:
                shutil.move(str(sdlc / ".git"), str(park))
        if not self.dry and sdlc.exists() and not any(sdlc.iterdir()):
            sdlc.rmdir()
        if not self.dry:
            self.git("add", "-A", "--", *[s for s in staged if (self.t / s).exists()])
        self.say("STAGED", f"{len(staged)} paths; review with `git status`, then commit")
        if (self.t / "CLAUDE.local.md").exists():
            self.todo.append("CLAUDE.local.md stays personal. Move what the team should share "
                             "(hard constraints, Workflow, Verifying your work) into CLAUDE.md, with paths "
                             "rewritten (.sdlc/intent/ -> intent/, .sdlc/x -> sdlc/x).")
        self.todo.append("CI workflows: python3 " + str(Path(sc.__file__)) + " . --plays ci" +
                         ("," + ",".join(plays) if plays else "") + " adds them (it skips what exists).")

    def unexclude(self):
        path = self.exclude_file()
        if not path.exists():
            return
        out, in_block = [], False
        for l in path.read_text().splitlines():
            if l == sc.EXCLUDE_MARKER:          # the block: marker, then "/path" lines
                in_block = True
                continue
            if in_block and l.startswith("/"):
                continue
            in_block = False
            out.append(l)
        while out and not out[-1].strip():
            out.pop()
        keep = [l for l in PERSONAL_EXCLUDES if l not in out]
        text = "\n".join(out) + "\n" + ("\n# personal Claude files\n" + "\n".join(keep) + "\n" if keep else "")
        self.say("UNEXCLUDED", "workflow paths in .git/info/exclude (CLAUDE.local.md, settings.local.json stay personal)")
        if not self.dry:
            path.write_text(text)

    def precommit_to_shared(self, staged):
        hook = self.git_path("hooks/pre-commit")
        asset = sc.PLAYS / "core/files/.githooks/pre-commit"
        if hook.exists() and self.ours(hook, ".githooks/pre-commit"):
            self.say("REMOVED", ".git/hooks/pre-commit (private copy)")
            if not self.dry:
                hook.unlink()
        dst = self.t / ".githooks/pre-commit"
        if not dst.exists():
            self.say("CREATED", ".githooks/pre-commit")
            if not self.dry:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, dst)
        staged.append(".githooks/pre-commit")
        cur = self.git("config", "--get", "core.hooksPath", check=False).strip()
        if not cur:
            self.say("SET", "git config core.hooksPath .githooks")
            if not self.dry:
                self.git("config", "core.hooksPath", ".githooks")
        elif cur != ".githooks":
            self.todo.append(f"core.hooksPath is {cur!r}: call .githooks/pre-commit from that hook.")

    # ---- shared -> private ---------------------------------------------------
    def to_private(self, history: bool):
        sdlc = self.t / ".sdlc"
        moves = []
        for name, dest in (("intent", ".sdlc/intent"), ("verify", ".sdlc/verify"), ("evals", ".sdlc/evals"),
                           ("sdlc", ".sdlc"), ("REVIEW.md", ".sdlc/REVIEW.md")):
            p = self.t / name
            if not p.exists():
                continue
            marker = {"verify": "verify/run.sh", "evals": "evals/run.py", "REVIEW.md": "REVIEW.md"}.get(name)
            if marker and not self.ours(self.t / marker, marker):
                self.say("LEFT", f"{name} (not installed by the workflow)")
                continue
            moves.append((p, Path(dest)))
        clash = [str(d) for s, d in moves if (self.t / d).exists() and (s.is_file() or
                 any((self.t / d / f.relative_to(s)).exists() for f in s.rglob("*") if f.is_file()))]
        if clash:
            raise SystemExit("error: destinations already exist: " + ", ".join(clash))
        removed = []
        for src, dest in moves:
            self.say("MOVED", f"{src.relative_to(self.t)} -> {dest}")
            removed.append(str(src.relative_to(self.t)))
            self.move(src, self.t / dest, sc.local_text)
        claude_files = self.workflow_claude_files()
        for r in claude_files:
            self.rewrite_file(self.t / r, sc.local_text)
        self.move_settings(".claude/settings.json", ".claude/settings.local.json", sc.local_text)
        settings_shared = self.t / ".claude/settings.json"
        wti = self.t / ".worktreeinclude"
        wti_ours = wti.exists() and self.ours(wti, ".worktreeinclude")
        if wti_ours and not self.dry and sc.LOCAL_WORKTREEINCLUDE not in wti.read_text():
            wti.write_text(wti.read_text() + sc.LOCAL_WORKTREEINCLUDE)
        workflows = [str(p.relative_to(self.t)) for p in (self.t / ".github/workflows").glob("*.yml")
                     if self.ours(p, str(p.relative_to(self.t)))] if (self.t / ".github/workflows").is_dir() else []
        # Index changes: stop tracking what becomes private; stage the rest.
        if not self.dry:
            untrack = removed + claude_files + ([".worktreeinclude"] if wti_ours else [])
            self.git("rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", *untrack)
            if workflows:
                self.git("rm", "-q", "--", *workflows)
            if settings_shared.exists():
                self.git("add", "--", ".claude/settings.json")
            elif self.tracked(".claude/settings.json"):
                self.git("rm", "-q", "--cached", "--", ".claude/settings.json")
        for w in workflows:
            self.say("REMOVED", f"{w} (CI is shared; it would break without verify/)")
        self.precommit_to_private()
        created = [Path(r) for r in claude_files] + ([Path(".worktreeinclude")] if wti_ours else []) \
            + [Path(".claude/settings.local.json")]
        sc.exclude(self.t, created, self.dry)
        if not (sdlc / ".git").exists():
            self.say("CREATED", ".sdlc/.git (private artifact history)")
            if history:   # replay into a scratch repo, then adopt its .git (keeps current files)
                if self.dry:
                    self.replay(self.t, "", self.t, "", sc.local_text)
                else:
                    tmp = Path(tempfile.mkdtemp(prefix="sdlc-history-"))
                    self.git("init", "-q", cwd=tmp)
                    self.replay(self.t, "", tmp, "", sc.local_text)
                    sdlc.mkdir(exist_ok=True)
                    shutil.move(str(tmp / ".git"), str(sdlc / ".git"))
                    shutil.rmtree(tmp, ignore_errors=True)
            if not self.dry:
                if not (sdlc / ".git").exists():
                    self.git("init", "-q", cwd=sdlc)
                self.git("add", "-A", cwd=sdlc)
                self.git("commit", "-q", "--no-verify", "-m", "Switch to private AI-native SDLC",
                         cwd=sdlc, check=False)
        self.say("STAGED", "removals of the shared workflow files; commit them when you're ready "
                 "(teammates will see that commit)")
        if (self.t / "CLAUDE.md").exists():
            self.todo.append("CLAUDE.md is the team's. Copy the sections you want to keep for yourself "
                             "(Hard constraints, Verifying your work, Workflow, Things Claude gets wrong) into "
                             "CLAUDE.local.md with paths under .sdlc/, and remove the Workflow section from "
                             "CLAUDE.md if the team no longer uses it.")

    def precommit_to_private(self):
        shared = self.t / ".githooks/pre-commit"
        cur = self.git("config", "--get", "core.hooksPath", check=False).strip()
        if shared.exists() and self.ours(shared, ".githooks/pre-commit"):
            if not self.dry:
                self.git("rm", "-q", "--", ".githooks/pre-commit")
            self.say("REMOVED", ".githooks/pre-commit")
            others = (self.t / ".githooks").is_dir() and any(
                p.name != "pre-commit" for p in (self.t / ".githooks").iterdir())
            if cur == ".githooks" and not others:
                self.say("UNSET", "core.hooksPath (was .githooks)")
                if not self.dry:
                    self.git("config", "--unset", "core.hooksPath")
                cur = ""
        if cur:
            self.todo.append(f"core.hooksPath is {cur!r}: no private pre-commit installed.")
            return
        hook = self.git_path("hooks/pre-commit")
        if hook.exists():
            self.todo.append(f"{hook} exists; private pre-commit not installed.")
            return
        self.say("CREATED", ".git/hooks/pre-commit (private)")
        if not self.dry:
            shutil.copy2(sc.PLAYS / "core/files/.githooks/pre-commit", hook)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--to", required=True, choices=["shared", "private"])
    ap.add_argument("--import-history", action="store_true",
                    help="replay intent/ history into the destination (commits in the project for --to shared)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t = Path(a.target).resolve()
    sw = Switch(t, a.dry_run)
    if subprocess.run(["git", "-C", str(t), "rev-parse", "--is-inside-work-tree"],
                      capture_output=True).returncode:
        print("error: not a git repo", file=sys.stderr)
        return 1
    cur = sw.layout()
    want = a.to
    if cur is None:
        print("error: no AI-native SDLC install found (run scaffold.py first)", file=sys.stderr)
        return 1
    if cur == want:
        print(f"already in the {want} layout")
        return 0
    print(f"SWITCH            {cur} -> {want}{' (dry run)' if a.dry_run else ''}")
    sw.to_shared(a.import_history) if want == "shared" else sw.to_private(a.import_history)
    for t_ in sw.todo:
        sw.say("TODO", t_)
    print("NOTE              hooks and settings changes apply in a new Claude Code session (or after /hooks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
