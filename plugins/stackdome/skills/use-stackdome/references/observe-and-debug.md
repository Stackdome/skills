# Observe and debug

Start with an authenticated, explicitly selected stack context. Keep every read bounded, preserve full IDs from structured output, and report exact non-sensitive reasons and messages. Do not run `--watch` or `--follow` in an agent procedure.

## Contents

- [Take a bounded snapshot](#take-a-bounded-snapshot)
- [Decide whether the attempt built and ran](#decide-whether-the-attempt-built-and-ran)
- [Diagnose a build failure](#diagnose-a-build-failure)
- [Diagnose a running resource](#diagnose-a-running-resource)
- [Restart and prove recovery](#restart-and-prove-recovery)
- [Cancel or roll back a release](#cancel-or-roll-back-a-release)

## Take a bounded snapshot

```bash
stackdome status -o json
stackdome status --conditions
stackdome logs <resource> --since 15m --tail 200
```

Structured status has `stack` and `live_status` at the top level. Compare `stack.latest_release` with `stack.converged_release` before diagnosing anything:

- `latest_release` is the newest attempt. It may be pending, failed, cancelled, or superseded without ever serving.
- `converged_release` is the release currently serving. A healthy older converged release does not make a newer failed attempt successful.
- `live_status` describes current runtime health. Resource failures are under `live_status.resources.<name>.last_failure`, not on the saved Stackfile resource.

Always state both release identities when they differ. A failed latest build or release and a runtime failure on an older converged release are separate facts and may be separate incidents. Do not attribute runtime logs from the older serving release to code from a newer attempt that never converged.

`stackdome status --conditions` is the human-readable table view with full condition history. `--conditions` adds no detail to JSON or YAML, so do not combine it with structured output. Start with the newest false or failing condition, retaining its type, reason, message, and transition time.

Runtime and build log commands stream finite history unless `--follow` is supplied. In table mode they print raw log lines. With `-o json`, each line is a separate JSON object shaped as `{"event": ..., "data": ...}`; it is a JSON Lines stream, not one JSON document or array. YAML is not supported for these log streams.

## Decide whether the attempt built and ran

Inspect the newest release once, then its recorded events:

```bash
stackdome list releases -o json
stackdome describe release <release-id> -o json
stackdome get release-events <release-id>
```

Use the full release ID. Release state and events establish which phase failed and may identify a build ID. A `Failed` release is not necessarily a build failure: validation, image build, apply, and readiness can all fail a release.

Use this evidence boundary:

| Failure class | Required evidence | Next bounded read |
| --- | --- | --- |
| Image build | A failed build record or explicit build failure in release/resource evidence. The attempted application image never ran. | Inspect the build record and build log below. |
| Main-container runtime crash | `live_status.resources.<name>.last_failure.type` is `runtime_crash` and its `container` detail identifies the failure. | Correlate its reason, message, restart count, and exit code with runtime startup logs. |
| Init-container failure | The resource failure contains `init_container` detail. | Report it as init-container failure, not as a main application crash; correlate its reason/message with conditions and any available relevant log evidence. |
| Readiness failure | The failure type is `readiness_failure`, or current conditions explicitly show readiness failing after the resource started. | Compare the condition reason/message with application startup and health-check logs. |

Do not classify a generic failed state more narrowly than its explicit evidence. In particular, do not guess Git authentication, Dockerfile, registry, application, or readiness causes from state alone.

For image-source validation failures, preserve the server's exact code and keep these distinctions:

- `registry_credentials_required`: no matching pull credential resolved and the registry rejected anonymous access; add or fix host/purpose coverage.
- `registry_auth_failed`: a configured credential resolved, but the registry rejected it; verify or rotate that credential.
- `image_not_found`: the probed reference did not exist or was not accessible; verify the complete tag or digest and repository access without claiming which of those two caused it.

If the external registry rate-limits the probe, Hub skips that preflight, withholds the checks-passed event, and allows the release to continue. Treat the image as unverified at that stage and still require the ordinary release and runtime convergence evidence.

## Diagnose a build failure

```bash
stackdome list builds -o json
stackdome describe build <build-id> -o json
stackdome logs build <build-id> --tail 200
```

Select the build linked from the failed release events or matching the resource and source revision; do not use an older failed build merely because it is recent. In the described build, inspect `status.state`, `status.conditions`, and `status.last_build_failure_detail`. That last field is best-effort and may be absent. Preserve its `failure_type`, `reason`, `message`, restart count, and `exit_code`, then cite the smallest relevant build-log excerpt. If neither detail nor logs identify the stage, report an unclassified build failure.

Build logs may not exist before the build job starts and may be pruned after completion. In either case, retain the build record and release events rather than substituting runtime logs.

## Diagnose a running resource

For a resource that started, use the matching entry from `live_status.resources`, table conditions, and bounded runtime logs together. Current `state`, replica counts, `observed_revision`, conditions, and `last_failure` show what Stackdome observed; the application log explains what the process emitted.

- A main-container crash can include `crash_loop`, out-of-memory, image-pull, container-creation, exit, or port-listening detail. Report only the captured value.
- An init-container failure blocks the main container from starting. Do not expect ordinary application startup lines.
- A readiness failure means the resource did not become ready; it does not prove the process crashed. Inspect the readiness condition and the application's health-check behavior.
- A healthy platform status does not prove the application's business behavior is correct. Use application-specific evidence when that is the incident.

## Restart and prove recovery

Take a pre-restart status snapshot and retain the resource's state plus `last_restart_request_processed_at`. Then request the restart:

```bash
stackdome restart <resource> -o json
```

The structured mutation result reports `restart_initiated`. It proves only that Stackdome accepted the request; it does not prove that a replacement process started or recovered.

Poll `stackdome status <resource> -o json` with a fixed deadline and a fixed maximum number of attempts. Require the resource to transition away from its pre-restart ready observation and back to ready, and require `last_restart_request_processed_at` to advance. Afterward, capture fresh startup evidence:

```bash
stackdome status <resource> -o json
stackdome logs <resource> --since 15m --tail 200
```

Report recovery only when the serving release remains the intended release, `live_status.health` is `ok`, the resource is ready again, the restart-processing timestamp advanced, and new startup log lines show the expected initialization. If the bounded deadline expires or the transition was not observed, report that verification is inconclusive rather than treating request acceptance as recovery.

## Cancel or roll back a release

Describe the release first and resolve the exact stack and full release ID. Cancellation is valid only for a pending release. Get target-specific confirmation before changing release state, then run:

```bash
stackdome cancel release <release-id>
stackdome describe release <release-id> -o json
```

Treat the cancellation result as the request result and verify the release's actual terminal state with the fresh description.

Rollback creates a new release from a historical released snapshot; it does not move history backward or roll back persistent data. List and describe releases first, then select a prior source whose own state is `Released`. Never select the failed release being recovered from merely because it is latest. Show the user that verified source release and target stack and get target-specific confirmation before running:

```bash
stackdome rollback release <release-id> --wait -o json
stackdome status -o json
```

`--wait` has a bounded CLI timeout. Retain the non-empty new release ID returned by the rollback, verify that it is distinct from the historical source ID, and never substitute the source ID in later checks. Report success only when the new release is terminal `Released`, is both the latest and converged release, and `live_status.health` is `ok`.

If Stackdome Cloud rejects an operation because of quota, capacity, or a disabled feature, preserve the non-sensitive server code, reason, and message. Treat it as a server-enforced platform constraint rather than an application failure. Server-enforced Cloud limits may differ, and self-hosted installations do not inherit them.
