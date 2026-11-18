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
| `emc:ai-native-sdlc-init` | Sets up the six-stage AI-native SDLC in a repo: intent.md, `/spec`, plan mode, `verify/run.sh` with post-edit + pre-commit hooks and CI, a reviewer agent + REVIEW.md, an approval-gate hook, docs/signals.md + `/triage`, CLAUDE.md workflow. |

## Adding a skill
`skills/<name>/SKILL.md` (frontmatter `name` + `description`), plus optional `scripts/`,
`assets/`, `references/`. Add a row above and bump `version` in `.claude-plugin/plugin.json`.
