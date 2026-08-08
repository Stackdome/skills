# Authoring rules

## Versioning

**Bump `version` in all four payload manifests on any PR that changes skill content or published plugin behavior:**

- `plugins/stackdome/.claude-plugin/plugin.json`
- `plugins/stackdome/.codex-plugin/plugin.json`
- `plugins/stackdome/.cursor-plugin/plugin.json`
- `plugins/stackdome/.grok-plugin/plugin.json`

Hosts use this version to detect updates. Without a bump, installed users keep the old skill no matter what lands here. CI fails if the four versions disagree.

## Layout

One payload directory, `plugins/stackdome/`, serves every host. Each host reads only its own `.<host>-plugin/plugin.json`; the others are inert. `skills/` and `hooks/` are discovered by convention — no manifest lists them.

Root catalogs point at the payload: `.claude-plugin/marketplace.json` (Claude Code), `.agents/plugins/marketplace.json` (Codex), `.cursor-plugin/marketplace.json` (Cursor). Grok resolves the payload through a remote source subpath from the xAI marketplace, so it needs no root catalog here — never add root-level copies or symlinks for it.

## SKILL.md

- It is a routing document, not a manual. Route by intent, give the commands an agent needs in the moment, and link the docs site for grammar and reference detail rather than duplicating it.
- Every CLI claim must match the installed CLI and https://docs.stackdome.com. When they disagree, the CLI wins — fix the claim.
- Document the traps, not just the happy path. A command that returns before the work finishes, ignores `-o json`, or exits `0` on interrupt will be misread by an agent unless the skill says so.
- Keep the `description` frontmatter broad enough to fire on operational asks — logs, scaling, debugging — not only on "deploy".
- Split into `references/*.md` when SKILL.md outgrows a single read. Until then, one file.

## Scope

- Never instruct an agent to handle a user's password, echo a secret value, or pass a destructive `--yes` without explicit confirmation for that specific action.
- Do not name any other company anywhere in this repo — code, comments, fixtures, docs, or commit messages.

## Verifying locally

```bash
# JSON validity, version parity, hook behavior
.github/workflows/ci.yml           # same checks CI runs
bash plugins/stackdome/hooks/auto-approve-stackdome.test.sh

# Install from a local checkout before pushing
/plugin marketplace add ./
/plugin install stackdome@stackdome-skills
```
