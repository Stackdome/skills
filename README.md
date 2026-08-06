# Stackdome Agent Skills

Skills that teach coding agents (Claude Code, Cursor, Codex, and any Agent Skills-compatible tool) how to work with [Stackdome](https://stackdome.com).

## Install

Host-agnostic (works everywhere):

```
npx skills add stackdome/skills
```

Claude Code:

```
/plugin marketplace add Stackdome/skills
/plugin install stackdome@stackdome-skills
```

Cursor / Codex: add this repo as a plugin source.

## Skills

| Skill | What it does |
|-------|--------------|
| `stackdome-deploy` | Deploys the current repo to a Stackdome instance: CLI install, token auth, stackfile authoring, deploy, verify. |

Docs: https://stackdome.mintlify.app
