# Resources and current CLI inventory

The current CLI is action-first. Prefer `stackdome <action> <noun>` and check `stackdome <action> <noun> --help` before using optional flags. `get` supports both collections and individual resources; `list` and `describe` are equivalent, narrower forms.

Never reveal a secret value, API token value, PostgreSQL credential, registry credential, or other credential-bearing output in chat, logs, tracked files, or an agent transcript. Before adding `--yes`, resolve the exact target, explain the irreversible effect, and get confirmation for that specific deletion. A general cleanup or deployment request is not confirmation.

Examples below show command shape, not Stackdome Cloud quota policy. Values accepted by one server are not guaranteed on another: server-enforced Cloud limits may differ, and self-hosted installations do not inherit them.

## Contents

- [Root commands](#root-commands)
- [Complete action/noun map](#complete-actionnoun-map)
- [Stack and release operations](#stack-and-release-operations)
- [Secrets](#secrets)
- [Volumes](#volumes)
- [PostgreSQL addons](#postgresql-addons)
- [API tokens](#api-tokens)
- [Context, export, and local tools](#context-export-and-local-tools)

## Root commands

| Area | Current root commands |
| --- | --- |
| Read resources | `get`, `list`, `describe` |
| Change resources | `create`, `update`, `delete` |
| Deploy and release | `apply`, `deploy`, `cancel`, `rollback` |
| Observe and operate | `status`, `logs`, `restart`, `open`, `backup` |
| Authentication and context | `signup`, `login`, `logout`, `whoami`, `ctx`, `use` |
| Local tooling and API access | `init`, `validate`, `export`, `doctor`, `api`, `completion`, `version` |
| Built-in help | `help` |

`logs` also has the `build` child for build logs. `completion` accepts `bash`, `zsh`, or `fish`. Route authentication details to [onboarding](onboarding.md), deployment to [Stackfiles and deployment](stackfiles-and-deploy.md), incident work to [observe and debug](observe-and-debug.md), and API-only capabilities to [API recipes](api-recipes.md).

## Complete action/noun map

| Action | Current nouns |
| --- | --- |
| `get` | `stacks`, `stack <stack>`, `builds`, `build <build-id>`, `releases`, `release <release-id>`, `release-events <release-id>`, `secrets`, `secret <name>`, `volumes`, `postgres-addons`, `postgres-addon <name>`, `postgres-backups <postgres-addon>`, `postgres-credentials <postgres-addon> <database>`, `tokens`, `token-scopes`, `config`, `stackfile-schema` |
| `list` | `stacks`, `builds`, `releases`, `release-events <release-id>`, `secrets`, `volumes`, `postgres-addons`, `postgres-backups <postgres-addon>`, `tokens`, `token-scopes` |
| `describe` | `stack <stack>`, `build <build-id>`, `release <release-id>`, `secret <name>`, `postgres-addon <name>` |
| `create` | `release`, `secret <name>`, `volume <name>`, `postgres-addon <name>`, `token <name>` |
| `update` | `secret <name>` |
| `delete` | `stack <stack>`, `secret <name>`, `volume <name>`, `postgres-addon <name>`, `token <token-id>` |
| `backup` | `postgres-addon <name>` |
| `cancel` | `release <release-id>` |
| `rollback` | `release <release-id>` |
| `export` | `stackfile <stack>` |
| `use` | `stack <stack>`, `context <instance-url>` |

For a collection, choose either `get <plural>` or `list <plural>` consistently. For one supported resource, choose either `get <singular> <id-or-name>` or `describe <singular> <id-or-name>`. Not every collection has an individual-detail command: use only the nouns listed above.

## Stack and release operations

Inspect scope and retain full IDs from structured output:

```bash
stackdome ctx -o json
stackdome list stacks -o json
stackdome describe stack <stack> -o json
stackdome use stack <stack>
```

`use stack` persists the selected stack. When `STACKDOME_URL`, `STACKDOME_TOKEN`, `STACKDOME_ORG`, or `STACKDOME_PROJECT` controls the session, pass `--stack <stack>` to stack-scoped commands instead of trying to persist a selection.

`apply` saves a Stackfile without releasing it. `deploy` saves and releases. `create release` releases the already saved state without applying a file:

```bash
stackdome apply --file stackfile.yaml -o json
stackdome deploy --file stackfile.yaml --wait -o json
stackdome create release --stack <stack> --wait -o json
```

Release and build reads are metadata and operational evidence:

```bash
stackdome list releases --stack <stack> -o json
stackdome describe release <release-id> --stack <stack> -o json
stackdome get release-events <release-id> --stack <stack>
stackdome list builds --stack <stack> -o json
stackdome describe build <build-id> --stack <stack> -o json
stackdome logs build <build-id> --stack <stack> --tail 200
```

Do not use unbounded `--follow` or `--watch` in agent procedures. See [observe and debug](observe-and-debug.md) before cancellation or rollback. Both change deployment state and require confirmation for the exact stack and release even though they do not use `--yes`:

```bash
stackdome cancel release <release-id> --stack <stack> -o json
stackdome rollback release <release-id> --stack <stack> --wait -o json
```

Deleting a stack permanently deletes that target. Describe it first, remove ambiguity, get target-specific confirmation, and only then add the bypass flag:

```bash
stackdome delete stack <stack> --yes -o json
```

## Secrets

Secret reads return metadata and key names, not values:

```bash
stackdome list secrets -o json
stackdome describe secret <secret-name> -o json
```

Do not put a value in a shell argument. Prepare an untracked, permission-restricted environment file outside the repository, do not display it, and pass its path:

```bash
stackdome create secret <secret-name> --from-file <secret-env-file>
stackdome update secret <secret-name> --from-file <secret-env-file>
```

The update replaces the secret's data with the supplied key/value set; it is not a merge. Never print the input file or structured mutation response, because secret-bearing server responses must be treated as sensitive even when later reads are redacted.

Before deletion, find every Stackfile reference, remove it, validate, deploy the change, and verify the running release no longer depends on the secret. Then get confirmation for the exact secret name before adding `--yes`:

```bash
stackdome delete secret <secret-name> --yes -o json
```

## Volumes

Volumes are stack-scoped. Inspect the target stack first and use an explicit size and access mode that the selected server accepts:

```bash
stackdome list volumes --stack <stack> -o json
stackdome create volume <volume-name> --stack <stack> --size <size> --access-mode <access-mode> -o json
```

Deleting a volume permanently destroys its stored data. Verify backups and every mount/reference, show the exact stack and volume, obtain target-specific confirmation, and only then run:

```bash
stackdome delete volume <volume-name> --stack <stack> --yes -o json
```

## PostgreSQL addons

PostgreSQL addons are project resources rather than stack-scoped CLI resources:

```bash
stackdome list postgres-addons -o json
stackdome create postgres-addon <addon-name> --database <database-name> --wait -o json
stackdome describe postgres-addon <addon-name> -o json
stackdome list postgres-backups <addon-name> -o json
```

`--wait` uses a bounded CLI timeout. Creation output and addon metadata are not substitutes for an application connection/readiness test.

For an on-demand backup, first save a structured pre-trigger snapshot of every existing backup's full `id`, `created_at`, and `started_at`. Then trigger the backup:

```bash
stackdome list postgres-backups <addon-name> -o json
stackdome backup postgres-addon <addon-name> -o json
```

The current handler accepts `--description` but ignores it, and its accepted response omits `backup_id`; table output can therefore show an empty ID. Do not use the description or trigger output to correlate a backup, and treat a successful trigger only as request acceptance.

With a fixed deadline and maximum attempts, poll `stackdome list postgres-backups <addon-name> -o json`, comparing full IDs with the pre-trigger snapshot and retaining each new record's timestamps and `phase`. The current schema exposes `pending`, `running`, `completed`, and `failed`; only `completed` proves success, while `failed` must be reported with its error. If exactly one new ID appears after the snapshot and reaches `completed`, report that record's ID, timestamps, and phase as the strongest available evidence, with the caveat that the server supplied no trigger correlation ID. If no new ID appears, more than one appears because of concurrent backups, or the new record's terminal phase cannot be proven before the bound expires, report the request as accepted but unverified or ambiguous; never claim that the requested backup completed.

This command returns sensitive, short-lived database credentials:

```bash
stackdome get postgres-credentials <addon-name> <database-name>
```

Do not run it through an agent channel, capture its output, quote it, or place it in a Stackfile. Hand the exact command to the human to run privately and store the result in an approved secret manager. `--superuser` produces more privileged credentials and requires a separately established need.

Deleting an addon permanently destroys its databases and storage. A backup request must finish successfully and satisfy the user's recovery requirements before it counts as protection. Resolve the exact addon, inspect backups and references, obtain target-specific confirmation, and only then run:

```bash
stackdome delete postgres-addon <addon-name> --yes -o json
```

## API tokens

Discover current server-defined scopes and inspect token metadata without exposing token values:

```bash
stackdome get token-scopes -o json
stackdome list tokens -o json
```

Token creation prints the sensitive token exactly once; it cannot be retrieved later:

```bash
stackdome create token <token-name> --scope <resource:action> --expires <duration>
```

Do not run token creation through an agent channel or capture its output. Have the human run the reviewed command privately, save the one-time value directly in an approved secret manager, and never paste it into chat or a tracked file. Use the narrowest current scopes and resource IDs that satisfy the job; discover them from the selected server rather than inventing scope names.

Revocation is immediate. Identify the token by metadata, show its exact ID and impact, obtain target-specific confirmation, and only then add `--yes`:

```bash
stackdome delete token <token-id> --yes -o json
```

## Context, export, and local tools

These commands inspect redacted context, change selections, or operate locally:

```bash
stackdome get config -o yaml
stackdome use context <instance-url>
stackdome ctx -o json
stackdome export stackfile <stack> --output-file <output-path>
stackdome get stackfile-schema -o json
stackdome init
stackdome validate --file stackfile.yaml
stackdome doctor -o json
stackdome open -o json
stackdome version -o json
stackdome completion <bash-or-zsh-or-fish>
```

Switching server context requires authentication again and can be blocked by environment-controlled context. `get config` redacts stored credentials. Export to a new path, review it, and validate it before replacing tracked state. Structured `open` prints URLs without launching a browser.

`signup`, `login`, `logout`, `whoami`, and context handoff rules are covered in [onboarding](onboarding.md). `stackdome api` is reserved for a documented endpoint with no purpose-built command; follow [API recipes](api-recipes.md), including its read-before-write and confirmation rules.
