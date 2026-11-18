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
| `emc:adlc-init` | Sets up the AI-native dev lifecycle in a repo: intent.md, `/spec`, verifier agent, post-edit + pre-commit verify hooks, docs/specs + docs/plans, CLAUDE.md workflow. |

## Adding a skill
`skills/<name>/SKILL.md` (frontmatter `name` + `description`), plus optional `scripts/`,
`assets/`, `references/`. Add a row above and bump `version` in `.claude-plugin/plugin.json`.
