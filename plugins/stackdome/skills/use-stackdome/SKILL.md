---
name: use-stackdome
description: Use for any Stackdome operation on a project deployed on, or targeting, Stackdome — first-time setup and deploy, shipping a change, checking whether an app is up, tailing logs, debugging a failed build or a crashing resource, scaling replicas, adding a worker or a cron job, custom domains and TLS certificates, preview environments for pull requests, managing secrets and environment variables, provisioning Postgres or a volume, database backups, minting API tokens, cancelling or rolling back a release, pointing the CLI at a self-hosted instance, or tearing a stack down. Use whenever the repo targets Stackdome — a stackfile.yaml or a Stackdome URL is enough — even if the user never says "Stackdome".
allowed-tools: Bash(stackdome:*), Bash(which:*), Bash(command:*), Bash(npm:*), Bash(npx:*), Bash(curl:*), Bash(python3:*)
---

# Use Stackdome

Stackdome is an application-delivery platform. You drive it through the `stackdome` CLI — never by editing cluster resources directly, and never by presenting Kubernetes as a user concern.

This file carries the procedure — what to run, in what order, and how to tell whether it worked. It does not carry reference detail. When you need a flag, a schema, a full failure explanation, or an endpoint, fetch it: https://docs.stackdome.com/llms.txt indexes every docs page and every API endpoint, each as its own `.md`. Canonical agent guide: https://docs.stackdome.com/guides/ai-agents.md.

**Not everything is in the CLI.** Custom domains, preview-environment enablement, and release rollback have no CLI command yet. They are not out of reach — the CLI is one client of the REST API and the dashboard is another, so anything the UI can do, the API can do. See [When the CLI has no command](#when-the-cli-has-no-command). **Never invent a CLI command** — a plausible-looking guess exits `4` and wastes the user's time.

## Output contract

`-o json|yaml` (default `table`) is global. With it, **stdout carries only the structured result**; prompts, progress, and warnings go to stderr. Parse stdout, keep stderr for diagnostics.

Three commands do not honour it. Assuming they do is the most common way to misreport state:

- `logs` writes raw application log lines to stdout — `-o json` does not wrap them in a schema.
- `restart` emits no structured result at all.
- `status --conditions` changes **table rendering only**. `status --conditions -o json` returns the same object as plain `status`, with no condition history. Read conditions in table mode.

**Never use `--follow` or `--watch`.** You have no way to interrupt a running command, so anything that does not return on its own hangs your session. `status --watch` never returns — it is an unbounded refresh loop. `logs -f` follows a live process, so it returns only when that process stops. `build logs -f` and `release events -f` do end on their own, but not until the build or release reaches a terminal state, which can be many minutes of a blocked session. Poll with bounded reads instead: `--since 15m --tail 200`, run again for a newer window.

Exit codes: `0` success, `1` general error, `2` auth/authorization, `3` not found, `4` invalid input or usage, `5` conflict, `130` canceled — including a confirmation the user declined.

## Routing

| User wants to… | Go to |
|---|---|
| First-time setup on a fresh or unknown instance | [Authenticate](#authenticate) → [Author the stackfile](#author-the-stackfile) → [Deploy](#deploy) |
| Ship a change | [Deploy](#deploy) |
| Know whether the app is up | [Observe](#observe) |
| Read logs | [Observe](#observe) |
| Debug a failed build | [Debug](#debug) → build failed |
| Debug a crashing or unhealthy resource | [Debug](#debug) → resource unhealthy |
| Debug a release that isn't progressing | [Debug](#debug) → release stuck |
| Run more or fewer copies of a resource | [Scale](#scale) |
| Add a background worker, a one-off job, or a cron job | [Workload types](#workload-types) |
| Grow a database or a volume | [Scale](#scale) |
| Get a public URL for the app | [Public URLs, domains, and TLS](#public-urls-domains-and-tls) |
| Add a custom domain, or fix a certificate | [Public URLs, domains, and TLS](#public-urls-domains-and-tls) — API, no CLI command |
| Set up preview environments for pull requests | [Preview environments](#preview-environments) — API, no CLI command |
| Deploy a specific git branch, tag, or commit | [Author the stackfile](#author-the-stackfile) |
| Set, rotate, or read env vars and secrets | [Secrets and environment](#secrets-and-environment) |
| Add Postgres, back one up, or add storage | [Databases and volumes](#databases-and-volumes) |
| Restart a resource | [Observe](#observe) → restart |
| Cancel a deploy in flight | [Releases and builds](#releases-and-builds) |
| Roll back to an earlier release | [Releases and builds](#releases-and-builds) — API, no CLI command |
| Mint a token, or switch instances | [Context and tokens](#context-and-tokens) |
| Tear something down | [Destructive operations](#destructive-operations) — confirm first |

## When the CLI has no command

The CLI is one client of the REST API; the dashboard is another. Anything the UI can do, the API can do — a missing CLI command is a gap in the CLI, not a limit of the platform.

1. https://docs.stackdome.com/llms.txt lists every endpoint by plain-English title, each linking to its own `.md` page. Read the one you need for the path, parameters, and body schema.
2. `stackdome whoami -o json` fills the path parameters: `server_url`, `organization_id`, `project`, `current_stack`.
3. Send it with the stored API token, interpolated rather than printed:

   ```bash
   curl -sS -H "Authorization: Bearer $(jq -r .access_token "${STACKDOME_CONFIG:-$HOME/.stackdome/config.json}")" \
     "<server_url>/api/v1/organizations/<organization_id>/..."
   ```

**`PUT` replaces the whole resource.** GET it, change the one field, PUT the complete object back. A partial body silently drops everything you omitted — a domains `PUT` built from just the new domain erases every existing one.

[Destructive operations](#destructive-operations) applies to API writes exactly as it does to CLI commands. Nothing else about using the API needs announcing to the user.

## Alpha scope

One organization, its default project, one connected cluster — and no selector for any of them. **Do not present organization, project, or cluster as a deployment choice.** Cloud is ephemeral and capacity-limited; self-hosted uses the identical stackfile and CLI workflow.

## Authenticate

**You never handle the user's password.** Interactive `login` and `signup` prompts need a real TTY, which your shell is not — `stackdome login` with neither `--token` nor both `--email` and `--password` exits `4` on non-interactive stdin.

1. **Check first** — `stackdome whoami -o json`. Returns a user, org, project, and auth method? You are done. Run this before any change, to confirm which server you are about to act on.
2. **Log in with a token.** Ask the user for their instance URL, and for a token from `<instance-url>/settings/api-tokens`:

   ```bash
   stackdome login --url <instance-url> --token <token>
   ```

   This persists the credential, so every later command in every later shell is authenticated. Confirm with `stackdome whoami -o json`.
3. **Exit code `2` later** — the token expired or was revoked. Ask for a new one and repeat step 2.

Never ask for their password, and never offer to type it for them. `stackdome signup --url <instance-url>` is for a human at a terminal creating an account — hand it to them, do not drive it.

**Why not environment variables:** `STACKDOME_URL` / `STACKDOME_TOKEN` / `STACKDOME_ORG` / `STACKDOME_PROJECT` are the documented path for CI, and they work there. They are the wrong tool for you: your shell does not persist state between commands, so an `export` in one call is gone by the next — and prefixing a command inline (`STACKDOME_TOKEN=… stackdome …`) makes it no longer start with `stackdome`, which forfeits the pre-approval that keeps `stackdome` commands from prompting. Mention them when writing a CI config; do not use them yourself.

## Install the CLI

Check first — this auto-approves and tells you whether there is anything to do:

```bash
stackdome version
```

Missing? The install is a piped shell script, so it needs the user's explicit go-ahead. Show them the line from https://docs.stackdome.com/get-started/cli and let them run it, or confirm before you do.

## Author the stackfile

Never write `stackfile.yaml` from scratch.

```bash
stackdome init
```

- A `docker-compose.yaml` / `compose.yaml` is converted automatically. **Read its warnings.** The conversion cannot carry a local build path: a compose `build: ./web` must become a git repository URL with a root-relative context, or the deploy fails at build time. This is the single most common first-deploy failure. `env_file` handling also needs checking.
- `--file/-f <path>` points at a non-default compose file; `--force` overwrites an existing stackfile.
- No compose file: you get a starter template. Fill it in from what the repo actually says — the Dockerfile, exposed ports, required env vars.

Full grammar: https://docs.stackdome.com/reference/stackfile.md

**Git sources** pin a revision per release. Use `branch:` or `tag:` (exactly one), optionally with `commit:`. Pin a commit for anything you need to redeploy identically later. **Pushing to git does not deploy** — there is no auto-deploy and no setting to enable one. Every release is one you asked for.

Gate every edit:

```bash
stackdome validate
```

Loop until it passes. `validate` is the authority, not your memory of the schema — unknown keys are hard errors, so a typo fails here rather than silently doing nothing.

A stackfile **describes and connects**. It never creates secrets or addons; those must already exist and are referenced by name. Create them first.

## Deploy

```bash
stackdome deploy --wait -o json
```

`--wait/-w` follows the release to a terminal state and exits non-zero if it does not reach `Released`. Without it, `deploy` returns as soon as the release is created, while it is still `Pending` — a state read at that moment says nothing about the outcome. `--file/-f` (default `stackfile.yaml`) and `--name` select a non-default stackfile or stack name.

**Retain `release.id` from the output.** Every check below needs it. If `deploy --wait` exits non-zero, the id is still in its output — use it to find out why rather than redeploying blind.

Release states: `Pending`, `InProgress`, `Released`, `Failed`, `Superseded`, `Cancelled`. Terminal: `Released`, `Failed`, `Superseded`, `Cancelled`.

### Verification contract

`Released` proves the release converged at some point. It does not prove it is still serving, nor that it is the newest attempt. Run:

```bash
stackdome status -o json
```

Then read the result against this table. `R` is your retained release id.

| What you see | What it means | What to do |
|---|---|---|
| `converged_release.id` == R, state `Released`, health `ok`, **and** `latest_release.id` == R with state `Released` | Deployed, healthy, newest | Report success. Give the user the URL |
| `converged_release` is null or absent | First deploy, nothing converged yet | Poll — see cadence below |
| `converged_release.id` != R, `latest_release.id` == R, latest state `Pending`/`InProgress` | Still rolling out; the old release is still serving | Poll |
| `converged_release.id` == R, health `progressing` | Rolling out normally — not a failure | Poll |
| `converged_release.id` == R, health `degraded` / `unavailable` / `failed` | Converged and broken | Do **not** report success. Go to [Debug](#debug) |
| `latest_release.id` != R | Someone else deployed after you; yours is superseded | Say so plainly. Do not report your deploy as live, and do not redeploy to "win" — ask |
| `latest_release.id` == R, latest state `Failed` | Your release failed | Go to [Debug](#debug) |

`health` is an enum — `ok`, `progressing`, `degraded`, `unavailable`, `failed`. Only `ok` is success and only `progressing` is worth waiting on; treating anything non-`ok` as broken reports a healthy rollout as a failure.

**Poll cadence:** `stackdome release info <release-id> -o json` every 10 seconds, up to 30 attempts (5 minutes). Still non-terminal after that? Stop polling and report the current state and the release id — a stuck release is a finding, not a reason to keep waiting silently.

Never claim a deploy succeeded on a state you did not observe yourself.

## Observe

| Command | Purpose |
|---|---|
| `stackdome status -o json` | Stack and resource status, once |
| `stackdome status <resource> -o json` | One resource |
| `stackdome status --conditions` | Condition history — **table mode only** |
| `stackdome logs [resource] --since 15m --tail 200` | Bounded log window — always bound it |
| `stackdome open [resource] -o json` | Print the public URL(s). **Always use `-o json`** — bare `open` tries to launch a browser you do not have |
| `stackdome restart <resource>` | Replace the running process |

Status proves platform health, not application correctness. A healthy release serving wrong answers is an application bug — read its logs.

### Verifying a restart

`restart` exits once the API accepts the request. It does **not** wait for the replacement to be ready, and returns no structured output. A zero exit proves acceptance, nothing more.

The trap: `stackdome status -o json` run immediately still describes the *old* process — `Released` and `ok` — while the replacement may already be crashlooping. A single healthy read right after a restart proves nothing.

Verify by observing the transition:

1. `stackdome status <resource> -o json` — wait for the resource to leave its ready state.
2. Poll until it re-enters ready (10s intervals, same 5-minute ceiling as above).
3. `stackdome logs <resource> --since 5m --tail 100` — confirm the new startup lines show what you expected.

If it never leaves ready, the restart may not have taken effect — say so rather than reporting success.

## Debug

`status -o json` carries a typed failure on each resource. Read the discriminator first — do not guess from prose.

```
resource.failure.type
├─ build_failure     → read .build          (never ran; no application logs exist)
├─ runtime_crash     → read .container
└─ readiness_failure → read .container, then the probe config
```

`.init_container` is a **separate slot** from `.container`. An init container failing looks like a resource that never starts and has no application logs — check it before concluding logging is broken.

| `failure_type` | Confirm with | Fix |
|---|---|---|
| `out_of_memory` | `reason` is `OOMKilled` | Raise the memory limit. A climbing `restart_count` means it is recurring, not a one-off |
| `port_not_listening` | app logs vs the stackfile's `ports` | The app listens on a different port, or binds `127.0.0.1` instead of `0.0.0.0` |
| `image_pull_failed` | `message` | Bad tag or digest, or a private registry with no credential |
| `create_container_error` | `message` | Bad command, missing mount, or an env reference that does not resolve |
| `crash_loop` | `restart_count`, `exit_code` | A symptom, not a cause — read the logs for what actually failed |
| `exit_error` | `exit_code` | Process exited non-zero; the logs carry why |

No `failure` on the resource? Route on release state instead:

| Evidence | Path |
|---|---|
| `latest_release.state` is `Pending` or `InProgress` | Release stuck — `stackdome release events <release-id>` (bounded, no `-f`), re-run for a newer window |
| `latest_release.state` is `Failed` | `stackdome release info <release-id> -o json`. Read **`validation_errors[]`** first: each carries `resource_name`, `field`, and a machine-readable `code` naming the exact bad stackfile field. That beats parsing `message` |
| A resource is not ready, with no typed failure | `stackdome status --conditions` (table mode), start at the newest false or failing condition, then `stackdome logs <resource> --since 15m --tail 200` and match its reason against the log lines |
| Newest release serving and healthy, app still wrong | Application logs. Platform health is not application semantics |

**Build failed** — three passes:

```bash
stackdome build list --resource <name> -o json    # find the id
stackdome build info <build-id> -o json           # structured evidence
stackdome build logs <build-id> --tail 200        # the failing step
```

From `build info`: `stack_resource_name`, `source_revision`, `build_context`, `status.state` (`Pending` | `Building` | `Success` | `Failed`), `status.conditions[]`, `status.last_build_failure_detail` (the `failure_type` table above), and `status.image_url` on success. The failure detail is best-effort and may be absent — the build log is the primary evidence for what the builder reported.

Runtime logs may be empty when a deploy fails before the resource ever runs. That is a build problem, not a logging problem.

Full guides: https://docs.stackdome.com/guides/build-failures.md and https://docs.stackdome.com/guides/status.md

## Workload types

Set `workload_type` on a resource. Default is `Service`.

| Type | Use for |
|---|---|
| `Service` | Long-running, receives traffic |
| `StatefulService` | Long-running with stable identity — databases, queues |
| `Worker` | Long-running, no ports — background processing |
| `Job` | Run-to-completion — migrations, one-off tasks |
| `CronJob` | Scheduled run-to-completion. Requires `schedule`, a five-field cron expression |

```yaml
  nightly-report:
    image: myorg/reporter:latest
    workload_type: CronJob
    schedule: "0 3 * * *"
```

## Scale

**There is no `stackdome scale` command.** Scale is declared in the stackfile and applied by a deploy — the same path as any other change, so it is versioned, reviewable, and travels with the release.

**Replicas** — an integer `>= 0` on the resource (`0` stops it without deleting it):

```yaml
resources:
  api:
    image: myorg/api:v1.2.0
    replicas: 3
```

```bash
stackdome validate && stackdome deploy --wait -o json
```

Verify per [Verification contract](#verification-contract).

**Postgres** — `--instances` at creation. The flag advertises `1-5`, but the supported shapes are **1 (single) or 2 (high availability)**; the product exposes no three-instance configuration. Do not set it above 2 without checking https://docs.stackdome.com/guides/postgres.md. `--storage` sets its disk. Reshaping a live addon is not a stackfile edit — check `stackdome addon postgres --help` before touching anything holding data.

**Volumes** — `size` lives in the stackfile's top-level `volumes` block. Growing storage is not always reversible; confirm with the user first.

**Alpha ceiling:** one cluster per organization, so horizontal scale is bounded by that cluster's capacity. If a resource cannot be scheduled, `status --conditions` says so — that is a capacity finding, not an application fault.

## Public URLs, domains, and TLS

To expose a resource: confirm the application's port from the repo or image, mark that port `public: true` in `stackfile.yaml`, validate, deploy, then `stackdome open <resource> -o json` for the URL. Verify release health and HTTPS afterwards.

**Custom domains have no CLI command.** They live as a `domains[]` array on the organization, so both reading and changing them go through the API — see [When the CLI has no command](#when-the-cli-has-no-command).

- Read: [`GET` an organization](https://docs.stackdome.com/api-reference/get-an-organization.md)
- Change: [`PUT` an organization](https://docs.stackdome.com/api-reference/update-an-organization.md) — **send the whole organization object**, with `domains[]` edited. A body containing only the new domain deletes every other one.

DNS still points at the user; you cannot create records for them. Certificate issuance follows domain setup, so a missing certificate on an org with no domain is that, not a bug.

Details: https://docs.stackdome.com/guides/domains-and-tls.md

## Preview environments

Per-pull-request previews have **no CLI command**, but a full API — see [When the CLI has no command](#when-the-cli-has-no-command).

| Job | Endpoint |
|---|---|
| Enable previews for a project | [Create a preview config](https://docs.stackdome.com/api-reference/preview-configs/create-a-new-preview-config.md) |
| Check whether they are enabled | [List preview configs](https://docs.stackdome.com/api-reference/preview-configs/list-preview-configs-for-a-project.md) |
| See the previews that exist | [List preview stacks](https://docs.stackdome.com/api-reference/preview-stacks/list-preview-stacks-for-a-project.md) |

Do the repo-side work first: author or update `stackfile.yaml` with the resources and public ports, and `stackdome validate` it to exit `0`. **`stackdome validate` passing does not mean previews are enabled** — check the preview config — and a plain `stackdome deploy` is not a preview. Do not describe either as one.

Details: https://docs.stackdome.com/guides/preview-environments.md

## Secrets and environment

Plain configuration goes in the stackfile's `env`. Anything sensitive is a secret object, referenced by name — a stackfile never contains a secret value.

| Command | Purpose |
|---|---|
| `stackdome secret list -o json` | List secrets — names only, never values |
| `stackdome secret info <name>` | One secret's metadata |
| `stackdome secret create <name> --from-file <path> --type <type>` | Create |
| `stackdome secret set <name> --from-file <path>` | Replace values — the previous value is unrecoverable |
| `stackdome secret delete <name>` | **Destructive** — see below |

`--type`: `Generic` (default), `DockerRegistry`, `GitCredentials`, `UsernamePassword`, `Token`, `SSHKey`.

**Use `--from-file`, not `--data KEY=VALUE`.** A value on the command line lands in the shell transcript and in your context. `--data` exists for a human at their own terminal; when you are handling the value, write it to a file the user provides or creates, pass the path, and never echo the value into your response, a log line, or a commit. This is the same rule as the password one — a secret you type is a secret you have leaked.

`secret set` overwrites: the previous value cannot be recovered. Confirm before rotating something in use. Rotations take effect on the next deploy of the resources that consume it.

## Databases and volumes

| Command | Purpose |
|---|---|
| `stackdome addon postgres list -o json` | List Postgres addons |
| `stackdome addon postgres info <name> -o json` | One addon's detail |
| `stackdome addon postgres create <name> --version <13-17, default 16> --storage <default 10Gi> --instances <1 or 2> --database <db> --superuser` | Provision |
| `stackdome addon postgres backup <name> --description <text>` | Trigger a backup |
| `stackdome addon postgres backups <name> -o json` | List backups |
| `stackdome addon postgres credentials <name> <database> -o json` | Live connection credentials (`--superuser` for elevated) |
| `stackdome addon postgres delete <name>` | **Destructive** — see below |
| `stackdome volume list -o json` | List volumes |
| `stackdome volume create <name> --size 5Gi` | Provision |
| `stackdome volume delete <name>` | **Destructive** — see below |

`addon postgres credentials` returns live database credentials. Treat the output as a secret: use it, never print it back.

`volume create` takes `--access-mode`, but every volume Stackdome creates is `ReadWriteOnce`, and the mode **cannot be changed after creation**. Leave the default unless the user has a specific reason and knows it is fixed for the volume's life.

An addon is managed by Stackdome. A database image declared as a resource in your stack is yours to operate and back up — do not describe the two as equivalent.

## Releases and builds

| Command | Purpose |
|---|---|
| `stackdome release list -o json` | Release history, newest first |
| `stackdome release info <release-id> -o json` | State, message, cause, validation errors, pins, outcome, snapshot |
| `stackdome release events <release-id>` | Event stream — bounded; do not use `-f` |
| `stackdome release cancel <release-id>` | Cancel a release — **only while `Pending`** |
| `stackdome build list -o json` | Build history (`--resource`, `--stack` to filter) |
| `stackdome build info <build-id> -o json` | One build's detail |
| `stackdome build logs <build-id> --tail 200` | Build log output |

`release cancel` works only while the release is `Pending`. Once it is `InProgress` the rollout has started and cancelling is no longer offered — deploy again, or roll back (see below). Cancelling is a mutation: confirm with the user first.

**Rolling back has no CLI command** — do not invent `stackdome release rollback`. It is the ordinary create-release endpoint with one extra field, [`POST` a new release](https://docs.stackdome.com/api-reference/releases/create-a-new-release-deploy.md) with `{"from_release_id": "<old-release-id>"}`, which copies that release's manifest. This is exactly what the dashboard's **⋮ → Rollback to this** does.

A rollback is a new release, not a restored old one — it gets its own id and sequence. Retain that id and verify it through [Verification contract](#verification-contract) like any other deploy.

A release pins what it deployed: a git source pins the commit, an image source pins the digest. `main` moving, or a tag being re-published, never changes an existing release — so the timeline is an honest record and a rollback is exact.

Every `release` subcommand takes `--stack <name>`. Use full IDs from structured output when automating; ID prefixes are an interactive convenience.

## Context and tokens

| Command | Purpose |
|---|---|
| `stackdome whoami -o json` | Current user, org, project, auth method |
| `stackdome config view` | Current CLI config |
| `stackdome config set-context <url>` | Point the CLI at a different Stackdome server |
| `stackdome config set-stack <stack>` | Default stack for this directory (name or ID) |
| `stackdome stack list -o json` | List stacks |
| `stackdome stack info <name> -o json` | One stack's detail |
| `stackdome token list -o json` | List API tokens |
| `stackdome token create <name> --scope <resource:action> --expires 720h` | Mint a scoped token (`--scope` and `--resource-id` repeatable; default lifetime is never) |
| `stackdome token scopes` | Valid `--scope` values |
| `stackdome token delete <id>` | **Destructive** — see below |

`token create` returns a live credential shown once. Hand it to the user; do not echo it into a summary or write it to a tracked file.

Most commands take `--stack/-s <name>` to target a stack other than the current context.

## Destructive operations

**Never pass `-y`/`--yes` before the user has confirmed that specific action.** Exit code `130` means they declined at the prompt — that is an answer. Do not re-run with `-y`, do not rephrase and retry, do not route around it with a different shell or script. Surface the decline and stop.

`destroy`, `stack delete`, `secret delete`, `volume delete`, `addon postgres delete`, and `token delete` are **irreversible**. The stack, credential, storage, or database behind them cannot be recovered. `secret set` and `release cancel` are also unrecoverable in effect, and need the same confirmation.

Before running any of them:

1. Name exactly what will be lost — which stack, secret, volume, database, or token — and say plainly that it cannot be undone.
2. Get explicit confirmation for that specific action. Not for "cleaning up", not implied by an earlier instruction.
3. Only then run it, adding `-y` so it can complete without a TTY prompt you cannot answer.

## Persisting context

Ask the user to commit `stackfile.yaml` — it is the source of truth for the stack, including replica counts, workload types, and volume sizes.

## Anything else

Read the docs rather than guessing. https://docs.stackdome.com/llms.txt lists every page; append `.md` to any docs URL for raw markdown. `stackdome <command> --help` is authoritative for flags — a flag on one command does not imply the same flag on another. When this file and the installed CLI disagree, the CLI wins.
