# Onboarding and context

Use a configured instance URL. Do not hard-code a Cloud host, ask a user to paste a **Full access** token into chat, handle passwords, or display a credential.

## Confirm that the CLI is installed

Start every workflow by checking the installed CLI:

```bash
stackdome version -o json
```

If the shell reports that `stackdome` is missing, stop before diagnostics or authentication. Do not install it automatically. Point the user to the [official CLI installation guide](https://github.com/Stackdome/stackdome-cli/blob/main/INSTALL.md), which currently covers macOS and Linux. Do not download or run the installer without explicit user confirmation. Explain before asking that the download contacts Stackdome's installer host, running it installs an executable, and it may update the user's shell profile to add the install directory to `PATH`. A general request to use or deploy with Stackdome does not approve installation.

After confirmation for the exact download, use the guide's agent-safe download-first sequence:

```bash
installer_file=$(mktemp)
trap 'rm -f "$installer_file"' EXIT
curl -fsSL https://get.stackdome.com/cli.sh -o "$installer_file"
```

After the download succeeds, let the user inspect the file and obtain separate confirmation for the exact install command:

```bash
sh "$installer_file"
```

Offer the guide's `--no-modify-path` option when profile changes are not wanted.

## Check the current state

Before authentication, use only the local/redacted diagnostics:

```bash
stackdome doctor -o json
stackdome get config -o yaml
```

`doctor` can reveal the configured server URL while distinguishing server, authentication, and scope/configuration failures; inspect its JSON result even when the expected missing-authentication checks make it exit nonzero. `get config` is also safe for local discovery because its structured output replaces every stored access or refresh token with `<redacted>`. `stackdome ctx` requires authentication, so do not use it to discover an instance before login.

After authentication, verify the identity and then read the authenticated context:

```bash
stackdome whoami -o json
stackdome ctx -o json
```

`whoami` verifies the active identity. `ctx` then shows the authenticated instance, organization, project, stack selection, and authentication source without revealing credentials.

## Human web handoff and local token login

For a new account, have the human run this on their own terminal:

```bash
stackdome signup --url <configured-instance>
```

For an existing account without a local token, have them run:

```bash
stackdome login --url <configured-instance>
```

Unauthenticated `signup` and tokenless `login` print instance-specific terminal instructions; they never open a browser. Tokenless `login` deliberately exits with validation code `4` after printing that handoff. This is the expected indication that a token is still required, not a failed token-login attempt. The human follows the printed handoff locally: visit the printed `<configured-instance>/sign-up` or `<configured-instance>/sign-in` URL, then create a **Full access** API token at the printed `<configured-instance>/settings/api-tokens` URL.

The human then runs the printed login command locally, without sharing the token in chat:

```bash
stackdome login --url <configured-instance> --token <full-access-api-token>
stackdome whoami -o json
```

The current CLI has no prompt or standard-input flag for token login: `--token` necessarily places the token in the local process arguments and may also record it in shell history. Never ask an agent, chat, or transcript to receive or substitute the token. Have the human use a trusted local terminal and follow that shell's secure-history practice while replacing the placeholder privately.

`whoami` is the required verification that the local token login worked. If it fails, run `stackdome doctor -o json` and act on the reported failure rather than retrying blindly.

## Switch instances

Inspect the current redacted configuration first. To select another instance, run:

```bash
stackdome use context <instance-url>
stackdome get config -o yaml
```

Changing context clears stored authentication for that instance. Use the redacted configuration output to confirm the selected URL, follow the web handoff above to authenticate it, then verify with `stackdome whoami -o json` and `stackdome ctx -o json`.

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
