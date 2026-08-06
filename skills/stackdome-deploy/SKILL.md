---
name: stackdome-deploy
description: Use when deploying an application to a Stackdome instance (self-hosted or cloud) — installs the CLI, authenticates with an API token, authors a stackfile from the repo, deploys, and verifies the release.
---

# Deploy to Stackdome

Stackdome is a self-hosted PaaS. You drive it entirely through the `stackdome` CLI. Canonical guide: https://docs.stackdome.io/guides/ai-agents.md — fetch it if anything here is unclear.

## 1. CLI

```
stackdome version || curl -fsSL https://get.stackdome.com/cli | sh
```

## 2. Authenticate

You need the instance URL and an API token. The user creates the token in a browser — you never handle passwords.

Ask: "Create an API token at `<instance-url>/settings/api-tokens` and paste it here."

```
stackdome login --url <instance-url> --token <token>
```

401 later? Token expired/revoked — ask for a new one from the same page.

## 3. Author the stackfile — always `init` first

Never write `stackfile.yaml` from scratch. Run:

```
stackdome init
```

- A `docker-compose.yaml`/`compose.yaml` in the repo is converted automatically (heed its warnings, e.g. `env_file` handling).
- Otherwise you get a starter template.

Then edit the generated file using what the repo tells you (Dockerfile, exposed ports, required env vars). Full grammar: https://docs.stackdome.io/reference/stackfile.md

Gate every edit with:

```
stackdome validate
```

Loop until it passes. `validate` is the authority, not your memory of the grammar.

## 4. Deploy and verify

```
stackdome deploy -o json
```

Success is machine-checkable: top-level `release.state == "Released"`. Then:

```
stackdome status -o json
```

Check `converged_release.state` and `.health`, and hand the user their app URL.

Failures: build issues → `stackdome build list` / `stackdome build info <id>`; crashing resources → `stackdome logs [resource]`. The guide's failure table covers the rest.

## 5. Persist

Ask the user to commit `stackfile.yaml`. Accept the AGENTS.md stanza `stackdome init` offers — future sessions start with context.

## Anything else

Fetch https://docs.stackdome.io/llms.txt, pick the relevant page, read its `.md` variant. Do not guess at flags or grammar — `--help` and `validate` are cheap.
