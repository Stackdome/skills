---
name: use-stackdome
description: Use for any Stackdome operation on a project deployed on, or targeting, Stackdome — self-host Stackdome, install Stackdome on a fresh Linux server with SSH access, configure the CLI for an existing Stackdome instance, first-time setup and deploy, ship a change, check whether an app is up, tail logs, debug a failed build or a crashing resource, scale replicas, add a worker or a cron job, configure custom domains and TLS certificates, prepare preview environments for pull requests, manage secrets and environment variables, provision Postgres or a volume, handle database backups, mint API tokens, cancel or roll back a release, or tear a stack down. Use whenever the user asks to self-host or install Stackdome, or a repo targets Stackdome — a stackfile.yaml or a Stackdome URL is enough — even if the user never says "Stackdome".
allowed-tools: Bash(stackdome:*), Bash(git rev-parse:*), Bash(git remote:*), Bash(git status:*), Bash(git branch:*), Bash(git push:*), Bash(openssl rand:*), Bash(docker build:*), Bash(docker push:*), Bash(ssh:*), Bash(curl:*), Bash(sh:*), Bash(sudo sh:*)
---

# Use Stackdome

Use a documented CLI command first; use `stackdome api` only for a documented endpoint without a CLI command. The current CLI is action-first: check `stackdome <command> --help` rather than inventing a noun-first command or optional flag.

Never handle passwords or echo credentials. Use structured output for reads, bound every log or poll window, and get explicit confirmation for the exact destructive or externally consequential action before adding `--yes`. In `-o json` mode, stdout is structured data and prose is on stderr; logs are JSON Lines and a restart result is acceptance, not recovery.

Stackdome Cloud custom-domain registration is unavailable; custom domains are self-hosted only. Cloud limits do not apply to self-hosted instances. Before the exact `docker push` to `ttl.sh`, warn that its public registry can expose image layers and get explicit confirmation.

## Route by intent

| Need | Reference |
| --- | --- |
| Install a new self-hosted Stackdome instance on a Linux server | [Self-hosted installation](references/self-hosted-install.md) |
| Install the CLI, use an existing instance, authenticate, switch context, or configure CI | [Onboarding and context](references/onboarding.md) |
| Inspect a repository, author a Stackfile, deploy, verify a release, or prepare previews | [Stackfiles, deployment, and previews](references/stackfiles-and-deploy.md) |
| Check status, read bounded logs, diagnose a failure, restart, cancel, or roll back | [Observe and debug](references/observe-and-debug.md) |
| Manage stacks, releases, builds, secrets, storage, PostgreSQL, tokens, or selections | [Resources and CLI inventory](references/resources.md) |
| Use a documented capability that has no CLI command | [API recipes](references/api-recipes.md) |
