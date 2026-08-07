---
name: stackdome-deploy
description: Use for any Stackdome CLI operation on a project that is deployed on, or targets, Stackdome — initial setup and deploy, checking status or logs, debugging a failed build or a crashing app, managing secrets and environment variables, provisioning a Postgres database or a volume, viewing app URLs/domains, restarting a resource, inspecting or rolling back releases, or tearing a stack down. Use whenever the user's project targets Stackdome, even if they don't say "Stackdome" explicitly.
allowed-tools: Bash(stackdome:*)
---

# Manage Stackdome apps

Stackdome is a self-hosted PaaS. You drive it entirely through the `stackdome` CLI — never edit cluster resources directly. Canonical guide: https://stackdome.mintlify.app/guides/ai-agents.md — fetch it if anything here is unclear or a command's exact behavior matters and you can't confirm it with `--help`.

Every command accepts `-o json|yaml` (default `table`); use `-o json` whenever you need to parse output instead of eyeballing it.

## Routing table

| User wants to... | Go to |
|---|---|
| First-time setup on a fresh/unknown instance | §Auth ladder → §Author the stackfile → §Deploy |
| Deploy / ship a change | §Deploy |
| Check if the app is up | `stackdome status -o json` |
| Tail or search logs | `stackdome logs` |
| Debug a build that failed | §Debugging recipes → build failed |
| Debug a crashing / unhealthy app | §Debugging recipes → app crashing |
| Set, rotate, or read env vars / secrets | §Day-2 operations → Secrets |
| Add a Postgres database | §Day-2 operations → Databases |
| Add persistent storage | §Day-2 operations → Volumes |
| Restart a resource | `stackdome restart <resource> -s <stack>` |
| Roll back, or inspect past releases | §Day-2 operations → Releases |
| Tear the stack down | §Destructive operations (confirm first) |

## Auth ladder

You never handle a password. Work down this list; stop at the first step that resolves.

1. **Check existing auth** — `stackdome whoami`. If it returns a user, you're done.
2. **Fresh instance, no account yet** — `stackdome signup --url <instance-url>`. Prompts the human for the remaining details on their own TTY; do not pass `--password` yourself.
3. **Account exists, human is present** — `stackdome login --url <instance-url>`. Prompts them for email/password on their TTY — you never see or type it.
4. **Headless, or a token is preferred** — ask the human to create one at `<instance-url>/settings/api-tokens`, then `stackdome login --url <instance-url> --token <token>`.
5. **Scoped token for automation** — `stackdome token create <name> --scope <resource:action>` (repeatable `--scope`, optional `--expires 720h`, `--resource-id`). Valid scope values: `stackdome token scopes`.
6. **401 later** — the token expired or was revoked. Go back to step 4 for a new one.

## CLI install

```
stackdome version || curl -fsSL https://stackdome.com/cli | sh
```

## Author the stackfile — always `init` first

Never write `stackfile.yaml` from scratch. Run:

```
stackdome init
```

- A `docker-compose.yaml`/`compose.yaml` in the repo is converted automatically (heed its warnings, e.g. `env_file` handling). Use `--file/-f <compose>` to point at a non-default compose file, `--force` to overwrite an existing stackfile.
- No compose file found → you get a starter template. Edit it using what the repo tells you (Dockerfile, exposed ports, required env vars). Full grammar: https://stackdome.mintlify.app/reference/stackfile.md

Gate every edit with:

```
stackdome validate
```

Loop until it passes. `validate` is the authority, not your memory of the grammar.

## Deploy

```
stackdome deploy --wait -o json
```

`--wait/-w` follows the release to a terminal state and exits non-zero if it doesn't reach `Released`. Without it, `deploy` returns immediately with the release still in its **initial** state (`pending`/`building`) — never report success off that.

Success is machine-checkable: top-level `release.state == "Released"`. If `--wait` was skipped or the shell timed out, poll `stackdome release info <release-id> -o json` until the state is terminal — never report a deploy successful without having observed `Released` yourself. `--file/-f` (default `stackfile.yaml`) and `--name` select a non-default stackfile or stack name. Then:

```
stackdome status -o json
```

Check `converged_release.state` and `.health`, and hand the user their app URL (`stackdome open` opens it in a browser).

## Day-2 operations

Most commands take `--stack/-s <name>` to target a stack other than the current context (`stackdome config set-stack` sets the default).

**Status & logs**

| Command | Purpose |
|---|---|
| `stackdome status -o json` | Stack + resource status, once |
| `stackdome status --watch/-w` | Live status |
| `stackdome status --conditions` | Include resource conditions (why something isn't healthy) |
| `stackdome logs` | Stream logs from the stack |
| `stackdome logs --follow/-f` | Keep streaming |
| `stackdome logs --since 5m\|1h` | Logs since a relative time |
| `stackdome logs --tail <n=100>` | Last N lines |

**Releases & builds**

| Command | Purpose |
|---|---|
| `stackdome release list -o json` | Release history |
| `stackdome release info <release-id> -o json` | One release's detail |
| `stackdome release events <release-id> --follow/-f` | Live release event stream |
| `stackdome release cancel <release-id>` | Cancel an in-flight release |
| `stackdome build list -o json` | Build history |
| `stackdome build info <id> -o json` | One build's detail |
| `stackdome build logs <id> --follow/-f --since --tail <n=200>` | Build log output |

**Secrets & environment variables**

| Command | Purpose |
|---|---|
| `stackdome secret list -o json` | List secrets (names only, no values) |
| `stackdome secret info <name>` | One secret's metadata |
| `stackdome secret create <name> --data KEY=VALUE --type <type>` | Create; `--data` is repeatable, or use `--from-file`, `--description` |
| `stackdome secret set <name> --data KEY=VALUE` | Update values; `--data` repeatable, or `--from-file` |
| `stackdome secret delete <name>` | **Destructive** — see below |

`--type` values: `Generic`, `DockerRegistry`, `GitCredentials`, `UsernamePassword`, `Token`, `SSHKey`.

**Databases (Postgres addon)**

| Command | Purpose |
|---|---|
| `stackdome addon postgres list -o json` | List Postgres addons |
| `stackdome addon postgres info <name> -o json` | One addon's detail |
| `stackdome addon postgres create <name> --version <13-17, default 16> --storage <default 10Gi> --instances <1-5> --database <db> --superuser` | Provision |
| `stackdome addon postgres backup <name>` | Trigger a backup |
| `stackdome addon postgres backups <name> -o json` | List backups |
| `stackdome addon postgres credentials <name> <database> -o json` | JIT connection credentials (`--superuser` for elevated) |
| `stackdome addon postgres delete <name>` | **Destructive** — see below |

**Volumes**

| Command | Purpose |
|---|---|
| `stackdome volume list -o json` | List volumes |
| `stackdome volume create <name> --size 5Gi --access-mode ReadWriteOnce\|ReadWriteMany\|ReadOnlyMany` | Provision |
| `stackdome volume delete <name>` | **Destructive** — see below |

**Stack, config & tokens**

| Command | Purpose |
|---|---|
| `stackdome stack list -o json` | List stacks |
| `stackdome stack info <name> -o json` | One stack's detail |
| `stackdome stack delete <name>` | **Destructive** — see below |
| `stackdome config view` | Show current CLI config |
| `stackdome config set-context <url>` | Switch to a different Stackdome server |
| `stackdome config set-stack <stack>` | Set the default stack for this repo (name or ID) |
| `stackdome token list -o json` | List API tokens |
| `stackdome token create <name> --scope <resource:action>` | Mint a scoped token |
| `stackdome token delete <id>` | **Destructive** — see below |
| `stackdome token scopes` | Valid `--scope` values |
| `stackdome whoami` | Current auth: user, org, project, method |
| `stackdome restart <resource> -s <stack>` | Restart a stack resource |
| `stackdome open [resource] -s <stack>` | Open a resource's public URL; with `-o json` it prints the URL(s) instead of launching a browser |

## Debugging recipes

| Symptom | Path |
|---|---|
| Build failed | `stackdome build list` → find the failed id → `stackdome build info <id>` → `stackdome build logs <id> --follow` for the raw output |
| App crashing / unhealthy | `stackdome status --conditions` to see why → `stackdome logs <resource> --since 10m` for the crash output |
| Release stuck / not progressing | `stackdome release events <release-id> --follow` for the live event stream |

## Destructive operations

`destroy`, `stack delete`, `secret delete`, `volume delete`, `addon postgres delete`, and `token delete` are **irreversible** — the underlying data, credentials, or storage cannot be recovered afterward. Each of these takes its own `-y`/`--yes` flag to skip the interactive confirmation prompt.

Before running any of them:

1. State exactly what will be lost (which stack/secret/volume/database/token, and that it cannot be undone).
2. Get explicit confirmation from the user for that specific action.
3. **Never pass `-y`/`--yes` on any of them on your own initiative.** That flag exists for the human's own scripts, to skip a prompt they already know about — it is not yours to use to skip asking.

The auto-approve hook only clears read-only commands, so any of these will still stop for the user's approval in the tool itself. Treat that prompt as intentional, not an error to route around — do not retry through a different shell, script, or flag combination to dodge it.

## Persist

Ask the user to commit `stackfile.yaml`.

## Anything else

Fetch https://stackdome.mintlify.app/llms.txt, pick the relevant page, read its `.md` variant. Do not guess at flags or grammar — `--help` and `validate` are cheap.
