# Stackfiles, deployment, and previews

Start only after [onboarding](onboarding.md) has established an authenticated context. Derive the Stackfile from repository evidence: inspect Dockerfiles, Compose files, runtime configuration, ports, dependencies, environment requirements, and persistent-data paths. Do not guess unsupported fields or source locations.

## Inspect the repository before choosing a build source

Before writing any `build` source, find the Git root and inspect its fetch remotes:

```bash
git rev-parse --show-toplevel
git remote -v
```

Run the second command in the returned Git root. Use an actual fetch URL, not a push-only URL. A remote is usable only when Stackdome can fetch it and the intended revision has been pushed. A local path, an absent remote, an inaccessible private repository, or an unpushed commit cannot back a Stackdome remote build. Private repositories require the corresponding Git integration. If no usable fetch remote can be established, do not create a remote `build` source or attempt deployment; use the decision gate below.

Stackdome build `context` and `dockerfile` paths are relative to the root of the cloned Git repository, not to the local working directory or Compose-file directory. Preserve the application topology found in Compose, but rewrite paths from the Git root.

## Create or edit the Stackfile

From the application directory, initialize a missing Stackfile:

```bash
stackdome init
stackdome validate --file stackfile.yaml
```

`init` converts a Compose file when it finds one, but conversion produces a draft. Review every warning and cross-check the draft against the Dockerfiles and application configuration. In particular, local Compose build paths do not become usable remote build sources automatically.

Every resource must contain exactly one source: either `build` or `image`, never both and never neither. A `build` needs a usable Git repository URL; an `image` needs a pullable OCI image reference. When exact fields are uncertain, inspect the CLI's embedded schema:

```bash
stackdome get stackfile-schema -o json
```

Run `stackdome validate --file stackfile.yaml` after every edit. Validation establishes only that the document is locally valid; it does not prove that a remote, image, secret, addon, or deployment destination is available.

To recover an existing saved definition without inventing noun-first commands, export it to a separate file and validate it before replacing tracked content:

```bash
stackdome export stackfile <stack> --output-file exported-stackfile.yaml
stackdome validate --file exported-stackfile.yaml
```

If the user wants to save a definition without changing the running workload, use:

```bash
stackdome apply --file stackfile.yaml -o json
```

`apply` creates or updates the saved stack only; it does not create a release.

## No usable remote: stop and choose a source

Offer these choices in order, and wait for the user's choice:

1. Create and push a Git remote that Stackdome can fetch. Inspect with `git status --short --branch`, `git branch --show-current`, and `git remote -v` first. Creating or changing a remote and pushing code are externally consequential actions: resolve and show the exact `git remote add <name> <url>` or `git remote set-url <name> <url>` command and the exact `git push --set-upstream <name> <branch>` command, then get explicit user confirmation before running each action. A general deploy request is not permission. If confirmation is absent, unclear, or refused, do not mutate the remote or push code; hand the commands to the user instead. After the user or agent completes the approved push, rerun the Git-root and fetch-remote checks and use a Git-root-relative `build` context.
2. Build locally and push to a private OCI registry the user controls. Confirm the registry integration can pull the exact reference, use its full image name in `image`, and never display registry credentials.
3. Only for temporary testing, build locally and push an auto-expiring image to `ttl.sh` under the gate below.

Do not silently substitute `ttl.sh` for a missing remote or infer consent for any remote mutation, Git push, or image push from a general request to deploy. Approval for a Git action does not approve a `ttl.sh` image push; that has the separate exact-image gate below.

### Temporary ttl.sh gate

Before any local Docker build intended for `ttl.sh`, inspect the Dockerfile, build context, and ignore rules for secret material. Stop if credentials or other secrets may enter the context or image, and do not print secret values.

Then give this warning before building or pushing: `ttl.sh` is an anonymous, unauthenticated OCI registry. Anyone who discovers or guesses the image name can pull it. Its publicly discoverable image layers may expose proprietary source, build artifacts, configuration, or accidentally embedded secrets. Images expire automatically; the default lifetime is one hour, a duration tag may request from one minute through 24 hours, and 24 hours is the maximum. Expiry makes later image pulls and redeploys fail even if the first deployment worked.

Generate a cryptographically random image name with at least 128 bits of entropy using `openssl rand -hex 16`, choose the shortest lifetime that fits the test, and form the full reference as `ttl.sh/<high-entropy-name>:<duration>`, for example with a `1h` duration tag. Show the user that exact full image reference and the exact `docker push <full-image-reference>` command. Ask for explicit confirmation for that exact image push. A general deployment approval or approval for a Git push is not confirmation. If confirmation is refused, unclear, or absent, do not build for `ttl.sh`, do not push, and do not edit the Stackfile to use the image.

Only after confirmation, use the confirmed reference unchanged:

```bash
docker build --file <dockerfile-path> --tag <confirmed-full-image-reference> <build-context>
docker push <confirmed-full-image-reference>
```

For each affected resource, remove the complete `build` block, add `image: <confirmed-full-image-reference>`, and run `stackdome validate --file stackfile.yaml` again. State the exact expiry when reporting the result and reiterate that any pull, restart onto an uncached node, or redeploy after expiry can fail.

## Deploy and prove the release

For an ordinary deployment, run:

```bash
stackdome deploy --wait -o json
stackdome status -o json
stackdome open -o json
```

Retain the non-empty `release.id` returned by `deploy`; do not substitute a previous release ID. A verified deployment requires all of the following:

- `deploy` exits successfully and its `release.state` is `Released`.
- Fresh `status` output has `stack.latest_release.id` and `stack.converged_release.id` both equal to the retained release ID, and both summaries are `Released`.
- `live_status.health` is `ok` for that converged release.
- For every expected public service, `open -o json` returns the intended non-empty entry in `urls`. Structured mode reports URLs without opening a browser.

Do not report success while latest and converged releases differ, health is missing or degraded, or an expected public URL is absent. Keep any follow-up polling bounded.

## Cloud rejection and self-hosted fallback

If Stackdome Cloud rejects the apply or release for quota, capacity, or a disabled feature, preserve the non-sensitive server error code, reason, message, and relevant status conditions as evidence. Explain that this is a server-enforced platform constraint; do not invent, publish, or rely on static Cloud quota numbers.

Offer the [self-hosted installation path](https://docs.stackdome.com/self-host/install) and reuse the same validated Stackfile and CLI workflow against that configured instance. Do not carry a Cloud quota or disabled-feature assumption into self-hosted Stackdome; its capacity and enabled features follow that installation's infrastructure and configuration.

## Prepare and verify previews

The CLI can prepare and validate the committed Stackfile only. It cannot enable preview automation or list, create, sync, or delete preview configurations or preview stacks. Route those documented operations to [API recipes](api-recipes.md) through `stackdome api`; do not invent preview CLI commands.

For automatic pull-request previews, require all of these boundaries:

- The repository is connected through a GitHub App installation. A plain public repository URL supports manual previews only.
- The validated Stackfile is committed at the configured path on the pull request head commit.
- The pull request targets the preview configuration's base branch.
- The pull request head is not from a fork; fork pull requests are intentionally not built.
- The destination has capacity for a complete copy of every resource and volume in the Stackfile.

After enablement or a lifecycle mutation, read the actual preview through the documented API. Do not treat local validation, a successful ordinary deployment, or an accepted asynchronous request as a running preview. Require the preview phase to be `Ready`, its reported commit (including `status.outputs.commit_sha` when present) to match the expected pull-request head, and every expected public resource to have a non-empty URL in `status.outputs.urls`. Surface the preview's returned failure reason and message when those checks do not converge.
