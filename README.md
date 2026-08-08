# Stackdome Agent Skills

Teach your coding agent to deploy, observe, debug, and scale applications on [Stackdome](https://stackdome.com).

The agent drives the `stackdome` CLI: it authors a stackfile from your repo, validates it, deploys, and verifies the release actually converged and is healthy — then tails logs, triages failed builds, scales replicas, and manages secrets, Postgres addons, and volumes.

## Install

**Claude Code**

```text
/plugin marketplace add Stackdome/skills
/plugin install stackdome@stackdome-skills
/reload-plugins
```

**Cursor** — Settings → Plugins → paste `https://github.com/Stackdome/skills`.

**Codex** — Plugins → More → Add more → enter `Stackdome/skills` as a marketplace source.

**Any Agent Skills-compatible tool**

```bash
npx skills add stackdome/skills
```

## What's in here

| Skill | Covers |
|---|---|
| `use-stackdome` | Authenticating, authoring and validating a stackfile, deploying and verifying a release, status and logs, build and runtime debugging, scaling, secrets, Postgres addons, volumes, releases and rollback, and safe teardown. |

A `PreToolUse` hook ships alongside it. It auto-approves read-only `stackdome` commands — `status`, `logs`, `whoami`, `validate`, and the `list`/`info` subcommands — so routine inspection doesn't interrupt you. Anything that mutates or destroys state stays behind the normal permission prompt.

## Layout

One payload, several hosts. Each host reads its own manifest and ignores the rest.

```text
.claude-plugin/marketplace.json     Claude Code catalog
.agents/plugins/marketplace.json    Codex catalog
.cursor-plugin/marketplace.json     Cursor catalog
plugins/stackdome/                  the payload every catalog points at
  .claude-plugin/  .codex-plugin/  .cursor-plugin/  .grok-plugin/
  hooks/                            PreToolUse auto-approval
  skills/use-stackdome/SKILL.md
```

## Docs

- Agent guide: https://docs.stackdome.com/guides/ai-agents
- Stackfile reference: https://docs.stackdome.com/reference/stackfile
- CLI reference: https://docs.stackdome.com/reference/cli
- All pages, machine-readable: https://docs.stackdome.com/llms.txt

## Contributing

See [AGENTS.md](AGENTS.md) for authoring rules — in particular, bump the plugin version on any change to skill content, or installed users never receive it.

Apache-2.0.
