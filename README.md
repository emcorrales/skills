# claude-skills

Personal Claude Code skills, packaged as one plugin (`emc`) with its own marketplace
(`emc-skills`).

## Install
```
/plugin marketplace add ~/projects/claude-skills
/plugin install emc@emc-skills
```
After editing a skill, run `/plugin marketplace update emc-skills` (or reinstall) to pick it up.

## Skills
| Skill | What it does |
|---|---|
| `emc:ai-native-sdlc-init` | Sets up the AI-native SDLC playbook in a repo as modular plays. `core`: per-change `intent/` → `/intent`, `/spec`, `/implement` (plan mode → plan.md), `/fix`; `verify/run.sh` feedback loop; guard, approval-gate and post-edit hooks; verifier agent; delivery metrics. Optional: `review` (REVIEW.md, reviewer, `/sweep-pr`), `ci`, `evals`, `maintain` (control bands → next intent.md). `--local` installs it privately: everything under `.sdlc/` (own git history), `settings.local.json`, `CLAUDE.local.md`, hidden via `.git/info/exclude`, so teammates see nothing. |

## Adding a skill
`skills/<name>/SKILL.md` (frontmatter `name` + `description`), plus optional `scripts/`,
`assets/`, `references/`. Add a row above and bump `version` in `.claude-plugin/plugin.json`.
