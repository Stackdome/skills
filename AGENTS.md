# AGENTS.md

Authoring rules for this repo.

- **Bump `version` in all three payload manifests** (`plugins/stackdome/.claude-plugin/plugin.json`, `plugins/stackdome/.cursor-plugin/plugin.json`, `plugins/stackdome/.codex-plugin/plugin.json`) on any PR that changes skill content. Hosts use this version to detect updates — without a bump, installed users get nothing.
- Keep the three manifest versions identical.
- No other company's name appears anywhere in this repo — comments, fixtures, or docs.
- `SKILL.md` links to the docs site (https://docs.stackdome.com) rather than duplicating its grammar or reference content inline.
