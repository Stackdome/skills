# Security

## Reporting a vulnerability

Email **hello@stackdome.com**. Please do not open a public issue for a security report.

Include what you did, what happened, and what you expected. A reproduction — the exact command string, or the exact skill instruction — is worth more than a description.

## What is security-sensitive here

**`plugins/stackdome/hooks/auto-approve-stackdome.sh` is a privilege boundary.** It decides which commands an agent may run *without* asking the user first. A command it approves executes with no prompt. Treat any of the following as a vulnerability:

- A command that is not a single, simple invocation of the `stackdome` CLI, yet gets approved — anything chained, piped, backgrounded, redirected, substituted, or commented.
- A command resolving to a binary other than the `stackdome` on `PATH` that gets approved.
- Any verb outside the read-only allow-list that gets approved, especially one that mutates or destroys state, or returns live credentials.

**`skills/use-stackdome/SKILL.md` shapes agent behaviour.** Instructions that would lead an agent to handle a user's password, echo a secret value or database credential into its output, or pass a destructive `--yes` without explicit confirmation are security defects, not documentation bugs.

## Scope

This repository packages instructions and a permission hook. It ships no server and stores no user data. Vulnerabilities in the Stackdome CLI or platform belong to those projects — but report them to the same address and we will route them.
