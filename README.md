# Xray Reality VPN Server Provisioning

[English](README.md) | [Русский](README.ru.md)

This is an Ansible setup for deploying an Xray VLESS + REALITY VPN server on a remote VPS.
It generates client configs for Clash Verge / FlClash (Mihomo Meta YAML) and Amnezia VPN (JSON).
Clash Verge and FlClash are the recommended daily drivers. Amnezia is a secondary option with known caveats.

## Where it runs

- Linux: through the bash wrapper, or directly with `ansible-playbook` (no client-config download that way).
- Windows: PowerShell wrapper + WSL.

---

## What this does

- Provisions a fresh Ubuntu/Debian VPS with Xray-core VPN server, VLESS protocol, and REALITY transport (stealth mode).
- Generates client configs and copies them to your local machine: Clash Meta YAML for Clash Verge / FlClash, JSON for Amnezia.
- Cleans up the local temporary workspace after the run. In `--full-cleanup` mode it also removes the packages it installed. It does not touch the VPS after configuration.

## Requirements

**Local machine:**

Linux:
- Ubuntu/Debian (or any distro with `apt`).
- SSH access to the target VPS.

Windows:
- WSL2 with Ubuntu/Debian (pre-installed).
- PowerShell 5.1+ (built-in on Windows 10/11).

**VPS:**
- Fresh Ubuntu 20.04+ or Debian 11+.
- Root or sudo.
- Public IP.

The wrapper installs Python 3, Ansible, and `sshpass` on your local machine if they are missing. On Windows, only WSL is required.

## Quick start

For the minimal case, you only need the VPS IP and password. Everything else is handled by the script.

### Linux / WSL (Bash)

Full help: `./provision-vpn.sh -h`

```bash
# SSH key, password from the key file.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa

# Only the host. Password will be prompted interactively with hidden input.
./provision-vpn.sh -H 1.2.3.4

# Inventory mode: pre-filled inventory.yml.
./provision-vpn.sh --use-inventory
```

### Windows (PowerShell)

Full help: `Get-Help .\Provision-VPN.ps1 -Full`

```powershell
# SSH key (Windows path; the wrapper converts it to the WSL path).
.\Provision-VPN.ps1 -HostName 1.2.3.4 -PKey C:\Users\You\.ssh\id_rsa

# Only the host. Password will be prompted interactively with hidden input.
.\Provision-VPN.ps1 -HostName 1.2.3.4

# Inventory mode.
.\Provision-VPN.ps1 -UseInventory
```

## Configuration

### Option 1: CLI parameters

```bash
./provision-vpn.sh -H <VPS_IP> -u <SSH_USER> -p <SSH_PORT> --pkey <PATH_TO_KEY>
```

Authentication: SSH key, password, or interactive password prompt (hidden). `--pkey` and `--pass` are mutually exclusive.

### Option 2: Inventory file

Edit `inventory.yml` and run with `--use-inventory`:

```yaml
all:
  hosts:
    your_host:
      ansible_host: 1.2.3.4
      ansible_user: root
      ansible_port: 22
      ansible_ssh_private_key_file: /path/to/key
      # ansible_ssh_pass: (use only if you don't have an SSH key)
```

Leave only one of `ansible_ssh_private_key_file` or `ansible_ssh_pass`. Setting both is an error.

In inventory mode the wrapper reads values from `inventory.yml` and ignores all CLI connection/auth parameters. On Windows, key paths in `inventory.yml` must already be valid from inside WSL (e.g. `/mnt/c/Users/You/.ssh/id_rsa`).

## Parameters

### Bash script

| Flag | Description | Required |
|------|-------------|----------|
| `-H, --host` | VPS IP / hostname | Yes (CLI mode) |
| `-u, --user` | SSH user | No (default: `root`) |
| `-p, --port` | SSH port | No (default: `22`) |
| `--pkey` | SSH private key path | No* |
| `--pass` | SSH password | No* |
| `--use-inventory` | Use `inventory.yml` instead of CLI arguments | No |
| `--clients-dir` | Local directory for downloaded client configs | No |
| `--cleanup` | Remove the temporary workspace (default) | No |
| `--full-cleanup` | Remove workspace + packages the script installed | No |
| `--no-cleanup` | Keep the workspace for debugging | No |
| `--debug` | Ansible `-vvv` + `xray_debug=true` | No |
| `--verbose` | Ansible `-vvvv` + `xray_debug=true` | No |
| `--dry-run` | Simulate the run inside WSL, no changes | No |

\* `--pkey` and `--pass` are mutually exclusive. If neither is given, the script prompts for a hidden password.

### PowerShell script

The same flags with PowerShell naming plus two extras:

- `-HostName` instead of `--host`
- `-PKey` instead of `--pkey`
- `-Pass` instead of `--pass`
- `-UseInventory` instead of `--use-inventory`
- `-ClientsDir` instead of `--clients-dir`
- `-CleanupMode` (`Default`, `Full`, `None`)
- `-LogLevel` (`None`, `Default`, `Verbose`)
- `-DryRun` — runs the bash script with `--dry-run` inside WSL. No system changes.

`-PKey` accepts an OpenSSH-format key readable from WSL. PuTTY `.ppk` files are not supported.

## Output

Local machine:
- Linux: `./downloaded-clients/*.json` and `./downloaded-clients/*.yaml`
- Windows: `.\downloaded-clients\*.json` and `.\downloaded-clients\*.yaml`

VPS:
- `/root/vpn-configs/*.json` (Amnezia) and `/root/vpn-configs/*.yaml` (Clash Verge / FlClash)

Recommended client: import `clash_client_*.yaml` into Clash Verge (Windows/macOS/Linux, TUN mode) or FlClash (Android).

Secondary, with caveats: Amnezia `client_*.json` exists but has known stability issues — Windows split-tunnel can crash the network stack, Android keepalive / background connectivity is unreliable. Use Clash Verge or FlClash unless you specifically need Amnezia.

References:
- Clash Verge: https://github.com/clash-verge-rev/clash-verge-rev
- FlClash: https://github.com/chen08209/FlClash
- Amnezia: https://github.com/amnezia-vpn/amnezia-client

## Advanced configuration

Edit `group_vars/all.yml` for granular control:

```yaml
num_clients: 3                        # Number of VPN profiles to generate
reality_camouflage_domain: dl.google.com  # Domain for REALITY transport obfuscation
warp_enabled: true                    # Enable Cloudflare WARP outbound
```

- `num_clients`: how many client configs to generate. Each gets a unique UUID. Increasing the value adds UUIDs to the persistent state; decreasing only hides the extras from generated configs.
- `reality_camouflage_domain`: legitimate domain that REALITY redirects suspicious connections to, making VPN traffic look like normal HTTPS.
- `warp_enabled`: enable the Cloudflare WARP outbound. WARP toggle is config-only — there is no CLI flag for it.

## Pinned image and WARP IPv4

The Xray Docker image is pinned to `teddysun/xray:26.6.27` (known-good). `:latest` is intentionally not used in production — an auto-update to 26.7.11 broke VLESS+REALITY compatibility in July 2026. To upgrade deliberately, change `xray_docker_image` in `group_vars/all.yml` (tag or digest `sha256:…`), test, then deploy.

The WARP outbound (`warp_ipv6: false`) defaults to IPv4-only for compatibility with VPS that have no IPv6 route. The WireGuard interface uses only IPv4 in that mode. `warp_endpoint: "162.159.192.1:2408"` is the Cloudflare WARP IPv4 anycast (stable name `engage.cloudflareclient.com:2408`). Override in `group_vars/all.yml` if needed.

`warp_enabled: true` requires `wgcf` 2.2.22, which the role downloads automatically. The persistent WARP credentials are `wgcf-account.toml` and `wgcf-profile.conf` under `/root/xray-config/`.

## Persistent identity

REALITY keys, short ID, and client UUIDs are persisted in `/root/xray-config/reality-state.json` (mode `0600`). Normal reruns keep the existing identity — client configs stay stable.

To rotate credentials, set `xray_reality_rotate: true` in `group_vars/all.yml` (or pass `-e xray_reality_rotate=true`). The old state is backed up with a timestamp, then a fresh identity is generated. Set the toggle back to `false` after the run. See [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md) for the full runbook.

## Security

- Sensitive files (`config.json`, `reality-state.json`, WARP profiles) use mode `0600` (root-only).
- Client configs in `/root/vpn-configs/` use mode `0640`.
- Real private keys and client UUIDs are stored only in `/root/xray-config/reality-state.json` — never in client configs.
- `--debug` and `--verbose` print extra diagnostic messages that include the `private_key` and `client_uuids` from `reality-state.json`. Use them deliberately and do not forward such logs.

## Post-deploy checks

After the run, the role runs a small set of non-fatal checks: the container uses the pinned image, the Xray TCP port is listening locally, and the Xray journal has no obvious errors. These checks do not validate a REALITY handshake or WARP egress. Confirm those with a real client from outside the VPS.

Secret rotation is documented in [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## More examples

```bash
# Custom SSH port and output directory.
./provision-vpn.sh -H vps.example.com -p 2222 \
  --pkey ~/.ssh/id_rsa --clients-dir ~/vpn-configs

# Dry run: script runs inside WSL with --dry-run, no system changes.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --dry-run

# Full cleanup: remove the workspace and packages the script installed.
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --full-cleanup
```

## Windows and WSL notes

- WSL2 with Ubuntu/Debian is required. The wrapper invokes the bash script through WSL.
- `-PKey` accepts an OpenSSH private key. Pass the Windows path; the wrapper converts it to `/mnt/<drive>/...` for WSL. PuTTY `.ppk` files are not supported.
- In inventory mode, the wrapper passes only `--use-inventory` to the bash script. The key path in `inventory.yml` must be a path that WSL can read. For Windows-stored keys, use `/mnt/c/...`.
- The default `--clients-dir` becomes `.\downloaded-clients\` next to the script. The wrapper creates it automatically.
- `-Pass` is never logged, even in `-LogLevel Verbose` or `-DryRun` output.

## Troubleshooting

**"Command not found: ansible"**
The script auto-installs it. If that fails:
```bash
sudo apt-get update && sudo apt-get install -y ansible
```

**"Permission denied (publickey)"**
Check the key permissions on the host you pass to the wrapper:
```bash
chmod 600 ~/.ssh/id_rsa
```
Test manually: `ssh -i ~/.ssh/id_rsa user@host`.

**"inventory.yml missing required fields"**
Fill all required fields in `inventory.yml` before running `--use-inventory`, or use CLI mode with `-H`, `--pkey`/`--pass`.

**Line endings (LF vs CRLF)**
Scripts enforce LF via `.gitattributes`. If you still see issues: `dos2unix provision-vpn.sh`, re-clone the repo, or open a GitHub issue.

## Contributing

Contributions are welcome. Use conventional commits. Test with `--dry-run` and a real run on your own VPS, including verifying the connection through a real client.

## Issues

Bug? Open an issue with:
- Your setup (Linux/Windows, bash/PowerShell version).
- Expected vs actual behavior.
- Steps to reproduce.
- Relevant logs.

Suggestion? Open an issue with:
- How you currently use the project.
- What you'd like to add.
- Whether you can test it yourself.

## License

AGPL-3.0 with a Commercial Use Restriction.
Free for personal use and non-commercial distribution.
Commercial use requires prior written permission from the author: **tim.korelov@yandex.com**.
Full text: [LICENSE](LICENSE) (English). Summary in Russian: [LICENSE.ru.md](LICENSE.ru.md).

## Author

Tim Korelov
https://github.com/lifestreamy
