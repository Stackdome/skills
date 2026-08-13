# Onboarding and context

Use a configured instance URL. Do not hard-code a Cloud host, ask a user to paste a **Full access** token into chat, handle passwords, or display a credential.

## Check the current state

```bash
stackdome whoami -o json
stackdome doctor -o json
stackdome ctx -o json
```

`whoami` verifies the active identity and authentication source. `doctor` distinguishes server, authentication, and scope/configuration failures; inspect its JSON result when it exits nonzero. `ctx` shows the active instance and selected context without revealing credentials.

## Human web handoff and local token login

For a new account, have the human run this on their own terminal:

```bash
stackdome signup --url <configured-instance>
```

For an existing account without a local token, have them run:

```bash
stackdome login --url <configured-instance>
```

Unauthenticated `signup` and tokenless `login` print instance-specific terminal instructions; they never open a browser. The human follows the printed handoff locally: visit the printed `<configured-instance>/sign-up` or `<configured-instance>/sign-in` URL, then create a **Full access** API token at the printed `<configured-instance>/settings/api-tokens` URL.

The human then runs the printed login command locally, without sharing the token in chat:

```bash
stackdome login --url <configured-instance> --token <full-access-api-token>
stackdome whoami -o json
```

`whoami` is the required verification that the local token login worked. If it fails, run `stackdome doctor -o json` and act on the reported failure rather than retrying blindly.

## Switch instances

Inspect the current context first. To select another instance, run:

```bash
stackdome use context <instance-url>
stackdome ctx -o json
```

Changing context clears stored authentication for that instance. Use the web handoff above to authenticate it, then verify with `stackdome whoami -o json`.

## CI

Configure these values in the CI provider's secret/environment mechanism, never in tracked files or command output:

```text
STACKDOME_URL
STACKDOME_TOKEN
STACKDOME_ORG
STACKDOME_PROJECT
```

`STACKDOME_URL` and `STACKDOME_TOKEN` supply an ephemeral authenticated context without persisting the token. `STACKDOME_ORG` and `STACKDOME_PROJECT` optionally provide the scoped context directly. Environment values override saved context, so do not try to switch context while they control the session. A CI job can verify its non-secret identity and scope with:

```bash
stackdome whoami -o json
stackdome ctx -o json
```
