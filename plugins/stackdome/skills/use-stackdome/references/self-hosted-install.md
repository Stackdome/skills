# Self-hosted installation

This path creates a new Stackdome platform. It is different from configuring the CLI for an existing Stackdome instance. Before acting, read the current [self-hosted installation documentation](https://docs.stackdome.com/self-host/install) for the released installer version and flags. Ground any changed command or prerequisite in that page and the current installer rather than guessing.

## Establish the target and prerequisites

The current installer targets one Linux `amd64` or `arm64` server. The operator needs SSH access and root or `sudo` on that server. The practical capacity floor is 2 CPUs, 4 GB of RAM, and 20 GB free on `/`. The host also needs:

- outbound internet access and `curl` on `PATH`;
- ports 80, 443, and 6443 free from non-k3s processes;
- inbound ports 80 and 443 allowed by its firewall or cloud security group; and
- a public IPv4 address that the server can discover through `ifconfig.me`.

A custom domain is optional. Without one, the installer selects a `stackdome.<public-ip>.nip.io` address. For a custom domain, follow the DNS preparation in the current install documentation before installation.

The installer installs or reuses local k3s on that Linux host. It does not install onto an arbitrary remote Kubernetes cluster such as EKS, GKE, or AKS. Do not confuse access to an existing Stackdome instance with access to an unrelated Kubernetes cluster, and do not promise an installation path the current installer does not implement.

Confirm that the SSH target is the intended server before changing it. Use read-only checks to verify its OS, architecture, privileges, ports, network access, CPU, memory, and free disk. If the agent does not have authorized SSH access, give the operator the checks to run in their trusted SSH session and wait for the results.

## Download, inspect, and install

Installing Stackdome is a privileged, externally consequential change: it installs k3s when absent, Helm when absent, cluster-scoped RBAC and CRDs, and the Stackdome control plane. Explain that scope before proceeding.

On the target server, obtain explicit confirmation before downloading the installer. Download it to a temporary file instead of piping a remote response directly into `sudo`:

```bash
installer_file=$(mktemp)
trap 'rm -f "$installer_file"' EXIT
curl -fsSL https://get.stackdome.com/install.sh -o "$installer_file"
sh -n "$installer_file"
```

Let the operator inspect the downloaded file. For deterministic automation, use the versioned installer URL named by the current install documentation rather than silently using the newest release.

Obtain separate explicit confirmation for the exact `sudo` command and its chosen admin email, domain, and optional flags. Prefer JSON output with a root-only credentials file so the generated credential is not printed in terminal output:

```bash
sudo sh "$installer_file" \
  --email admin@example.com \
  --output json \
  --credentials-file /root/.config/stackdome/bootstrap.json
```

Replace the example email with the operator-approved admin address. Add `--domain stackdome.example.com` only after its DNS is ready. The agent must not read or display the credentials file, and must not redirect human-mode output because it contains the generated credential.

## Verify and hand off to the existing-instance workflow

Exit code `0` and a final JSON object with `status` equal to `installed` confirm that the installer completed. Preserve the returned URL, organization, and cluster identifiers, but never expose credential contents. The installer itself waits for local k3s, the Stackdome agent, and the API health endpoint; its result also means it created the `Default` organization, connected the `local` cluster, and provisioned its in-cluster build registry.

Have the human retrieve the generated admin credential privately from the protected file and sign in at the returned instance URL. Then return to the existing-instance workflow in [Onboarding and context](onboarding.md): install the CLI on the workstation if needed, select the new URL, have the human create a **Full access** API token without sharing it, verify `stackdome whoami -o json`, and only then author and deploy the first Stackfile.
