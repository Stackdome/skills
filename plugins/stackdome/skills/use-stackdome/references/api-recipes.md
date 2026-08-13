# Hub API recipes

Use this reference only for a documented Hub capability that has no purpose-built CLI command. Prefer the CLI workflow elsewhere in this skill whenever one exists. The API is permission-scoped and deployment-specific; an endpoint appearing here is not evidence that the active identity may call it or that Stackdome Cloud enables it.

## Contents

- [Safe request pattern](#safe-request-pattern)
- [High-value reads](#high-value-reads)
- [Preview environments](#preview-environments)
- [Source and registry integrations](#source-and-registry-integrations)
- [Object stores](#object-stores)
- [Advanced PostgreSQL administration](#advanced-postgresql-administration)
- [Projects, membership, admins, and invites](#projects-membership-admins-and-invites)
- [Self-hosted compute administration](#self-hosted-compute-administration)
- [Custom domains](#custom-domains)

## Safe request pattern

Start with the authenticated context and retain `organization_id` and `project` from its structured result:

```bash
stackdome whoami -o json
```

Use list and detail GETs to resolve every other ID. Do not guess an ID from a display name or reuse one from another organization or project.

`stackdome api` accepts exactly one relative path beginning with `/api/`. Do not pass a host, scheme, protocol-relative URL, fragment, or path outside that prefix. It supplies the configured authentication itself; never extract a token or replace this command with raw authenticated `curl`.

```bash
stackdome api '/api/v1/users/current' -o json
stackdome api '/api/v1/users/current/projects' -o json
```

Default and `-o json` API output are the server's raw JSON bytes, not a CLI table and not pretty-printed CLI JSON. Only `-o yaml` parses a JSON response and converts it to YAML. Parse the documented response schema rather than assuming table-shaped rows.

Before any write:

1. Open the current [Stackdome API reference](https://docs.stackdome.com/api-reference), find the exact method and path, and inspect its current `requestBody` and success response schema. This file is a recipe index, not a substitute for OpenAPI.
2. GET the target and any referenced resources. Preserve required fields, read-only boundaries, current revision or state, and the exact IDs returned by the server.
3. Put every nontrivial body in a JSON file and pass `--data-file`; do the same for every secret-bearing body, even when it is short. Never place a secret in `--data`, shell history, chat, a tracked file, or output. Never ask for, accept, echo, or store a password or token. A human or approved local secret-aware mechanism must materialize secret placeholders in an untracked mode-`0600` file and remove it afterward.
4. Show the user the resolved method, path, target, intended changes, and consequences. Get explicit approval for that exact destructive or externally consequential operation. A general request is not approval to delete data, change access, send an invite, contact an external provider, create infrastructure, or interrupt a database.
5. Only after that approval, add `--yes`. Without it, mutating methods prompt interactively and fail closed on non-interactive input.
6. Read the resource again and verify documented state and effects. A `201`, `200`, or asynchronous `202` proves acceptance only.

The generic write form is:

```bash
# Run only after explicit approval for this exact METHOD and PATH.
stackdome api '/api/v1/organizations/{org_id}/...' \
  -X METHOD --data-file request.json --yes -o json
```

Replace every brace placeholder and URL-encode path or query values that need it. Do not send the braces literally.

## High-value reads

All calls in this section are GETs. Use `?stream=false` for one bounded metrics snapshot; do not use `stream=true` through this recipe.

### Runtime graph and metrics

| Path template | Purpose and response guidance |
| --- | --- |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stacks/{id}/metrics?stream=false` | One `ResourceMetrics` snapshot aggregated for the stack. Here `{id}` is the stack ID. `cpu_usage` is a string in **millicores**, `memory_usage` is bytes; also inspect `timestamp`, `assigned_nodes`, and `node_capacities`. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stacks/{id}/resources/{resource_name}/metrics?stream=false` | The same bounded `ResourceMetrics` shape for one named resource; `{id}` is the stack ID. The resource segment is its name, not its ID. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stacks/{id}/topology` | `StackTopology`: `nodes` plus explicit and derived `edges`; `{id}` is the stack ID. Use node refs, edge `kind`, `source_of_truth`, mappings, and non-sensitive output descriptors to explain the graph; an output descriptor is not its value. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stacks/{id}/connections` | `StackConnectionList`: only user-authored connections in `items`, with `total`; `{id}` is the stack ID. Inspect `from`, `to`, `kind`, `mappings`, and `config`; use topology when derived edges also matter. |

### Git and registry integrations

| Path template | Purpose and response guidance |
| --- | --- |
| `/api/v1/organizations/{org_id}/git-integrations` | `GitIntegrationList`; retain integration `id`, `type`, `host`, `status`, `credentials_configured`, and GitHub App `install_url`. Stored auth material is not returned. |
| `/api/v1/organizations/{org_id}/git-integrations/{id}` | One integration before verification, rotation, or deletion. Here `{id}` is the integration ID. |
| `/api/v1/organizations/{org_id}/git-integrations/{id}/installations?refresh=false` | GitHub App installations; `{id}` is the integration ID. Use `refresh=true` only when deliberately re-listing from GitHub after a suspected missed webhook. |
| `/api/v1/organizations/{org_id}/git-integrations/{id}/repositories?page={page}` | Repositories visible across installations; `{id}` is the integration ID. Use returned `items`, `page`, `total_count`, and `has_next`. Add `installation_id={git_installation_uuid}` to scope it. |
| `/api/v1/organizations/{org_id}/git-integrations/{id}/repositories/{owner}/{repo}` | Repository details including `clone_url`, `default_branch`, privacy, and last push time; `{id}` is the integration ID. |
| `/api/v1/organizations/{org_id}/git-integrations/{id}/repositories/{owner}/{repo}/branches` | `GitBranchList` for choosing an existing branch; `{id}` is the integration ID. Do not infer a branch from local state. |
| `/api/v1/organizations/{org_id}/registry-credentials` | `RegistryCredentialList`; retain `id`, normalized `host`, `purpose`, and `username`. The write-only `password` is not returned. |
| `/api/v1/organizations/{org_id}/registry-credentials/{id}` | One credential's non-secret metadata before verification, rotation, or deletion. Here `{id}` is the credential ID. |

### Object stores and previews

| Path template | Purpose and response guidance |
| --- | --- |
| `/api/v1/organizations/{org_id}/object-stores` | Cross-project object stores visible to the caller. Use it for discovery, then use the project-scoped detail route for mutation. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/object-stores` | Project `ObjectStoreList`; inspect `id`, `name`, `spec`, and `status.state`/`status.message`. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/object-stores/{id}` | One complete object-store configuration before update or deletion; `{id}` is the object-store ID. Credential fields are secret references, not secret values. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs?page={page}&page_size={page_size}` | Paged preview configurations. Retain the configuration ID and verify repository, base branch, integration, Stackfile path, and active-preview policy. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs/{id}` | One preview configuration before update or deletion. Here `{id}` is the configuration ID. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/preview-stacks?page={page}&page_size={page_size}` | Paged previews; optionally add `config_id={config_id}`. Inspect source, branch, commit, status, and deletion timestamp. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/preview-stacks/{id}` | Authoritative preview lifecycle state, failure reason/message, deployed commit, and public URLs. Here `{id}` is the preview ID. |

### Access and compute state

| Path template | Purpose and response guidance |
| --- | --- |
| `/api/v1/users/current/projects` | Projects accessible to the active identity; use alongside `whoami`, not as a substitute for it. |
| `/api/v1/organizations/{org_id}/users?page={page}&page_size={page_size}` | Organization users and their IDs for membership/admin operations. |
| `/api/v1/organizations/{org_id}/projects` | Organization project list. |
| `/api/v1/organizations/{org_id}/projects/{project_name}` | One project before rename or deletion. |
| `/api/v1/organizations/{org_id}/projects/{project_name}/members` | Project memberships and membership IDs. The `{id}` in member update/delete routes is the membership ID. |
| `/api/v1/project-roles` | Current assignable project roles; do not invent a role string. |
| `/api/v1/organizations/{org_id}/admins` | Current organization admins before promotion or demotion. |
| `/api/v1/organizations/{org_id}/invites?status={status}` | Invites, optionally filtered by `pending`, `accepted`, `revoked`, or `expired`. |
| `/api/v1/organizations/{org_id}/invites/{id}` | One invite before resend or revocation. Here `{id}` is the invite ID. |
| `/api/v1/organizations/{org_id}/clusters` | Organization-owned compute list. An empty/inapplicable result can reflect deployment compute policy, not unrestricted permission to add compute. |
| `/api/v1/organizations/{org_id}/clusters/{id}` | One cluster's non-secret metadata and embedded registry state. Here `{id}` is the cluster ID. Hub responses omit stored CA/token credentials. |
| `/api/v1/organizations/{org_id}/image_registries` | Organization-wide cluster-registry list. These are in-cluster build registries, not external registry credentials. |
| `/api/v1/organizations/{org_id}/clusters/{cluster_id}/image_registries` | Registries for one cluster. |
| `/api/v1/organizations/{org_id}/clusters/{cluster_id}/image_registries/{id}` | One registry and its `spec`, `status.state`, and conditions. Here `{id}` is the registry ID. |

## Preview environments

### Configure automatic or manual previews

Use `POST /api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs` with `StackPreviewConfigCreate`. Required fields are `name` and `git_repository`; available fields are:

- `git_repository.repo_url` (required), `git_repository.base_branch`, and `git_repository.integration_id`
- `description`, `stackfile_path`, and `max_active_previews`
- `env` entries with required `name`, optional literal `value`, and optional `self_output`; apply the usual secret-safety rules to any literal value
- `labels` and `annotations` entries with `key` and `value`

Automatic pull-request previews require `git_repository.integration_id` to identify a connected `github_app` integration. A plain public `repo_url` with no GitHub App supports manual preview creation only. Before automatic enablement, verify the integration and installation can see the repository, the configured base branch exists, the pull-request head is not a fork, the validated Stackfile is committed at `stackfile_path` on the head commit, and the destination has capacity for a complete copy of the Stackfile.

Use `PUT /api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs/{id}` with `StackPreviewConfigUpdate`; `{id}` is the configuration ID. Its writable fields are `description`, `stackfile_path`, `max_active_previews`, `git_repository`, `env`, `labels`, and `annotations`; `name` is not in the update schema. This PUT replaces the writable configuration: GET first, preserve every unchanged writable field in the request, change only the approved fields, and omit the GET response's IDs, `name`, and timestamps.

After explicit approval for enabling or changing the exact repository automation:

```bash
stackdome api '/api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs' \
  -X POST --data-file preview-config.json --yes -o json

stackdome api '/api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs/{id}' \
  -X PUT --data-file preview-config-update.json --yes -o json
```

### Manual lifecycle

Use these current operations:

| Operation | Method and path | Current request fields |
| --- | --- | --- |
| Create | `POST /api/v1/organizations/{org_id}/projects/{project_name}/preview-stacks` | `PreviewStackCreate`: required `config_id`, `pr_number`, `branch`; optional `commit`, `stackfile_content`, `image_overrides`. |
| Sync | `POST /api/v1/organizations/{org_id}/projects/{project_name}/preview-stacks/{id}/sync` | `{id}` is the preview ID. Optional `PreviewStackSync`: `commit`, `stackfile_content`, `force_sync`, `image_overrides`. |
| Delete | `DELETE /api/v1/organizations/{org_id}/projects/{project_name}/preview-stacks/{id}` | `{id}` is the preview ID. No body; returns asynchronous acceptance. |
| Delete config | `DELETE /api/v1/organizations/{org_id}/projects/{project_name}/stack-preview-configs/{id}` | `{id}` is the configuration ID. No body. Read previews that use the config before approval. |

Creation, sync, and deletion are externally consequential and may start builds, releases, or teardown. Obtain exact approval before `--yes`. When optional Stackfile content or image overrides are needed, use a request file rather than constructing JSON in the shell.

For create or sync, retain the returned preview ID and poll the detail GET for a bounded period. Report success only when `status.phase` is `Ready`, `commit` and `status.outputs.commit_sha` when present match the expected committed head, and every expected public resource has a non-empty entry in `status.outputs.urls`. On `Failed`, surface `status.reason` and `status.message`. A `202`, local Stackfile validation, or an ordinary released stack is not proof of a ready preview.

Preview deletion has a different terminal condition: an accepted delete may first return the preview in `Deleting`. Poll the detail GET until it returns `404`, or confirm the preview ID is absent from a fresh project preview list; do not require `Ready` or report deletion from `202`/`Deleting` alone. After deleting a configuration, verify its detail GET returns `404` and it is absent from the configuration list separately.

## Source and registry integrations

### GitHub App

Start the current flow with `POST /api/v1/organizations/{org_id}/git-integrations/github/manifest`; it has no request body and returns `GitHubAppManifestFlow` fields `github_url`, `state`, and sometimes `manifest`.

This is a browser callback workflow, not a blind API sequence. In a per-organization app flow, a human browser must POST the returned manifest to `github_url`, approve GitHub's app creation, follow `/api/v1/git-integrations/github/manifest/callback`, then install the app. In a platform-wide app flow, `github_url` is the install page. The setup callback at `/api/v1/git-integrations/github/setup` is unauthenticated but state-validated and is not an agent-synthesized call. Popups, provider approval, installation selection, one-time state, and callbacks can require an interactive signed-in browser. Hand off rather than replaying or fabricating callback parameters.

After explicit approval to begin that external GitHub flow:

```bash
stackdome api '/api/v1/organizations/{org_id}/git-integrations/github/manifest' \
  -X POST --yes -o json
```

Finish by listing integrations and installations, then list the intended repository and branches. Automatic previews require the resulting GitHub App integration ID.

### Token/basic Git integrations

Use `POST /api/v1/organizations/{org_id}/git-integrations` to create and `PUT /api/v1/organizations/{org_id}/git-integrations/{id}` to rotate; `{id}` is the integration ID. The current `GitIntegration` body uses:

- `host` (required)
- `type`: `git_credentials` or `github_app`
- for credential integrations, `auth` containing exactly one of `token` or `basic`; `basic` contains `username` and `password`

Auth fields are write-only. Keep them only in the protected request file, never in an example value or result. Direct update supports `git_credentials` only; `host` and `type` are immutable. GET first, send the current required `host`, keep `type` unchanged if supplied, include `auth` only when rotating it, and omit read-only response fields. Verify with `POST /api/v1/organizations/{org_id}/git-integrations/{id}/verify` and `GitIntegrationVerifyRequest` field `repo_url`, then read the integration again.

Delete with `DELETE /api/v1/organizations/{org_id}/git-integrations/{id}` only after checking stacks, preview configurations, and repositories that depend on it and obtaining explicit approval.

### External registry credentials

Use `POST /api/v1/organizations/{org_id}/registry-credentials` to create and `PUT /api/v1/organizations/{org_id}/registry-credentials/{id}` to rotate; `{id}` is the credential ID. The current `RegistryCredential` fields are `host`, `purpose` (`pull`, `push`, or `both`), `username`, and write-only `password`. `host` and `username` are required; creation requires the write-only credential. `host` and `purpose` are immutable on update. GET first, preserve the current required `host` and current `purpose` when present, send the current or approved new `username`, and omit read-only response fields. Do not include the write-only field in an update unless exact credential rotation was approved; omission retains the server-side value.

Keep the write-only value as a protected request-file placeholder, never an inline argument:

```json
{
  "host": "registry.example.com",
  "purpose": "pull",
  "username": "<registry-user>",
  "password": "<materialize-locally-from-approved-secret-source>"
}
```

Verify with `POST /api/v1/organizations/{org_id}/registry-credentials/{id}/verify`; `RegistryCredentialVerifyRequest` uses required `repository` and optional `purpose`. Verification contacts the external registry, so obtain approval before `--yes`.

Before `DELETE /api/v1/organizations/{org_id}/registry-credentials/{id}`, GET the credential and affected stacks. Deletion is not blocked by implicit use; its `RegistryCredentialDeleteResponse.affected_stacks` reports stacks that had resolved through it. Explain that impact and obtain approval first.

## Object stores

Object stores are PostgreSQL backup destinations, not stack volumes. Create with `POST /api/v1/organizations/{org_id}/projects/{project_name}/object-stores`; update with `PUT /api/v1/organizations/{org_id}/projects/{project_name}/object-stores/{id}`, where `{id}` is the object-store ID. Both use the current `ObjectStore` shape: required `name` and `spec`; `spec` requires `destination_path` and `configuration`, with optional `retention_policy`. `name` is immutable on update.

Choose exactly one configuration branch:

- `s3_credentials`: required `access_key_id`, `secret_access_key`, and `region`; optional `endpoint_url`
- `azure_credentials`: required `connection_string`; optional `storage_account_name`
- `gcs_credentials`: required `service_account_credentials`

Every credential field above is a `SecretReference` with exact fields `secret_id` and `key`. Reference an existing Generic secret; never put a cloud credential itself in the body. A safe S3-shaped request file looks like:

```json
{
  "name": "backup-store",
  "spec": {
    "destination_path": "s3://example-bucket/postgres",
    "retention_policy": "<policy-supported-by-current-endpoint>",
    "configuration": {
      "s3_credentials": {
        "access_key_id": {"secret_id": "<secret-uuid>", "key": "<access-key-field>"},
        "secret_access_key": {"secret_id": "<secret-uuid>", "key": "<secret-key-field>"},
        "region": "<region>",
        "endpoint_url": "<omit-for-aws-or-set-s3-compatible-url>"
      }
    }
  }
}
```

GET before PUT and preserve the current immutable `name` plus the complete writable `spec`; change only approved spec fields and omit IDs, status, organization/project IDs, and timestamps. After create/update, read until `status.state` is `Ready`; on `Error`, report `status.message`. Before `DELETE /api/v1/organizations/{org_id}/projects/{project_name}/object-stores/{id}`, find PostgreSQL addons that reference it, detach them through an approved addon update, and obtain approval. The API refuses deletion while an addon still uses it.

## Advanced PostgreSQL administration

Prefer purpose-built PostgreSQL CLI commands for supported create, read, backup, credential, and delete workflows. Use this API section only for update, fencing, and hibernation fields the CLI does not expose.

GET `/api/v1/organizations/{org_id}/projects/{project_name}/addons/postgres/{id}` first; `{id}` is the addon ID. Before preparing a PUT, inspect `spec.initialization`. The current Hub update validator rejects a non-empty existing initialization whether the request repeats it or omits it: repeating it is treated as an attempted immutable change, while omission changes it to empty. If the GET contains a non-empty `spec.initialization`, stop and report that this addon's API update is currently unsupported; do not call PUT.

Only when existing `spec.initialization` is empty, update with `PUT` on that same path using the current full `PostgresAddon` request shape. Preserve writable top-level `name`, `labels`, and `annotations`, and preserve the complete supported `spec`; omit read-only `id`, organization/project/user/cluster IDs, namespace, revision, outputs, and timestamps, and omit server-managed `status`. The body requires `name` and `spec`; `spec` requires:

- `version`: `major`, optional `minor`, `enable_auto_minor_upgrade`, `enable_auto_major_upgrade`
- `instances`: required `count`; optional `placement` with `topology_key`, `policy` (`preferred` or `required`), `node_selector`, and `tolerations` entries (`key`, `operator`, `value`, `effect`)
- `storage`: required `size`; optional `storage_class`

Other current `spec` fields are `resources.cpu.request`/`limit`, `resources.memory.request`/`limit`, `backup.enabled`/`object_store_id`/`schedule`/`wal_archiving`, `databases` entries with `name`/`extensions`, `configuration.enable_superuser_access`/`parameters`, and `initialization`.

Build the PUT file from the fresh GET's writable metadata and complete supported spec. Change only supported mutable fields. Name, version, storage size/class, and initialization are immutable after creation; do not attempt to smuggle changes into the full body. Review instance count, placement, compute/memory requests, backup destination/schedule, WAL archiving, databases/extensions, and superuser access for consequences before approval. Verify returned `revision`, `status.observed_revision`, state, message, and conditions rather than treating the PUT response as convergence.

Fencing and hibernation deliberately interrupt database behavior:

| Operation | Method and path | Exact body fields |
| --- | --- | --- |
| Fence/unfence | `POST /api/v1/organizations/{org_id}/projects/{project_name}/addons/postgres/{id}/actions/fence` | `{id}` is the addon ID. Required boolean `fence`; optional string `reason`. |
| Hibernate/wake | `POST /api/v1/organizations/{org_id}/projects/{project_name}/addons/postgres/{id}/actions/hibernate` | `{id}` is the addon ID. Required boolean `hibernate`. |

Read application dependencies and current addon state, explain the interruption, and get explicit approval for the exact direction before `--yes`. Then GET the addon in a bounded poll and require the intended `status.state`; surface status reason/message/conditions on failure.

## Projects, membership, admins, and invites

These operations change access or external communication. Resolve organization, user, project, membership, and invite IDs with the GET recipes; read `/api/v1/project-roles`; show the exact principal, role, and scope; then get explicit approval before `--yes`.

| Operation | Method and path | Current request schema fields |
| --- | --- | --- |
| Create project | `POST /api/v1/organizations/{org_id}/projects` | `ProjectCreateRequest`: required `name`. |
| Rename project | `PUT /api/v1/organizations/{org_id}/projects/{project_name}` | `ProjectUpdateRequest`: required new `name`. |
| Delete project | `DELETE /api/v1/organizations/{org_id}/projects/{project_name}` | No body; inspect all project resources first. |
| Add project member | `POST /api/v1/organizations/{org_id}/projects/{project_name}/members` | `AddProjectMemberRequest`: required `user_id`, `role`. |
| Change member role | `PUT /api/v1/organizations/{org_id}/projects/{project_name}/members/{id}` | `{id}` is the membership ID. `UpdateProjectMemberRoleRequest`: required `role`. |
| Remove member | `DELETE /api/v1/organizations/{org_id}/projects/{project_name}/members/{id}` | `{id}` is the membership ID. No body. |
| Promote org admin | `POST /api/v1/organizations/{org_id}/admins` | `PromoteAdminRequest`: required `user_id`. |
| Demote org admin | `POST /api/v1/organizations/{org_id}/admins/{user_id}/demote` | `DemoteAdminRequest`: required `project_name`; optional `role` (server default is Viewer). |
| Resend invite | `POST /api/v1/organizations/{org_id}/invites/{id}/resend` | `{id}` is the invite ID. No body; re-queues external email. |
| Revoke invite | `DELETE /api/v1/organizations/{org_id}/invites/{id}` | `{id}` is the invite ID. No body; pending invites only. |

Do not automate invite creation with `stackdome api`. The create endpoint returns a raw one-time `invite_token`, and this CLI writes successful API response bytes directly to stdout; until a redacted creation path exists, hand creation to a human using the dashboard and do not run a command that prints that token. Agents may safely list or GET invites. The current resend endpoint returns `200` with no response body, so after exact approval it may be used to re-queue email without exposing a token; if the current OpenAPI ever adds a token-bearing resend response, hand resend off too. Revoke only a confirmed pending invite after approval. Verify invite state with a safe list/detail GET after every accepted resend or revoke.

## Self-hosted compute administration

Compute registration is a self-hosted BYOC operation. Do not try to add tenant compute to Stackdome Cloud or assume that an empty list grants that capability. Confirm the configured instance is self-hosted, its compute mode accepts organization-owned clusters, the target Kubernetes API is reachable from the Hub, and `stackdome-agent` is installed before proposing a write.

Create compute with `POST /api/v1/organizations/{org_id}/clusters`. The current `Cluster` request requires `name`, `cluster_url`, `cluster_ca_data`, and `cluster_sa_token`; optional `cluster_image_registry` uses required `name` and optional `spec.backend_storage_size`/`spec.backend_storage_class`. `cluster_url` must be the Hub-reachable HTTPS API URL. `cluster_ca_data` and `cluster_sa_token` are secret-bearing; use protected local placeholders only:

```json
{
  "name": "<cluster-name>",
  "cluster_url": "https://<hub-reachable-kubernetes-api>",
  "cluster_ca_data": "<materialize-locally-base64-ca-data>",
  "cluster_sa_token": "<materialize-locally-service-account-token>",
  "cluster_image_registry": {
    "name": "<registry-name>",
    "spec": {
      "backend_storage_size": "<size>",
      "backend_storage_class": "<storage-class>"
    }
  }
}
```

Creating compute writes infrastructure and stores high-privilege credentials. Obtain explicit approval for the exact cluster and registry configuration before `--yes`. After creation, GET the cluster and registry until the registry reaches its documented running state; inspect conditions on pending/error states. The response intentionally omits the stored CA and service-account token.

There is no cluster update or credential-rotation endpoint. `DELETE /api/v1/organizations/{org_id}/clusters/{id}`, where `{id}` is the cluster ID, is delete-then-reconnect recovery, not migration: it does not move workloads or data and removes the in-cluster registry before the record. Inventory dependent stacks/addons, back up required data, explain the impact, and obtain explicit approval.

Create an additional registry with `POST /api/v1/organizations/{org_id}/clusters/{cluster_id}/image_registries` using `ClusterImageRegistry` fields `name` and optional `spec.backend_storage_size`/`backend_storage_class`. Delete with `DELETE /api/v1/organizations/{org_id}/clusters/{cluster_id}/image_registries/{id}`, where `{id}` is the registry ID, only after checking build/deployment dependencies and approval. Verify through the registry detail GET and its status/conditions.

## Custom domains

Stackdome Cloud custom-domain registration and update are unavailable. Do not search for a hidden Cloud endpoint, fabricate a domain body, or attempt either operation with `stackdome api`.

Discuss custom-domain registration or update only for a self-hosted Stackdome instance. Follow the current [domains and TLS guide](https://docs.stackdome.com/guides/domains-and-tls) and that instance's current documented API/Stackfile contract; if no matching endpoint appears in its current OpenAPI schema, stop rather than inventing one. Cloud limits do not apply to self-hosted instances, whose capacity and feature configuration come from that installation.
