# Xray Reality VPN Server Provisioning

**Fully automated Ansible setup for deploying an Xray Reality VPN server on a remote VPS.**

> Generates client configs for Clash Verge / FlClash (Mihomo Meta YAML) and Amnezia VPN (JSON). Clash Verge & FlClash are the recommended clients; Amnezia is secondary with known caveats (see [Advanced Configuration](#advanced-configuration)).

## Runs On 
- Linux
  - Through the bash wrapper
  - Or with the `ansible-playbook` command (does not download client configs to your machine by itself, do it yourself)
- Windows — PowerShell wrapper + WSL

---


## What This Setup Does

- Provisions a fresh Ubuntu/Debian VPS with Xray-core VPN server and VLESS protocol with Reality transport (stealth mode)
- Auto-generates and exports client configs: Clash Meta YAML (`.yaml`) for Clash Verge/FlClash + JSON (`.json`) for Amnezia VPN
- Cleans up afterward, reverting only the changes it made 


## Requirements

**Local Machine:**

*Linux:*
- Ubuntu/Debian-based system (or any distro with `apt`)
- SSH access to target VPS

*Windows:*
- WSL2 with Ubuntu/Debian (must be pre-installed)
- PowerShell 5.1+ (built-in with Windows 10/11)

**VPS:**
- Fresh Ubuntu 20.04+ or Debian 11+ installation
- Root or sudo access
- Public IP address

> **Note:** The provisioning script automatically installs required dependencies (Python 3, Ansible, sshpass) on your local machine. You only need WSL on Windows.

## Quick Start

**For the minimal case scenario you would need the VPS IP and password, everything else is done by the script.**

The wrapper scripts allow for easy launch both from Windows and from Linux.

### Linux/WSL (Bash)

To get full help message in CLI use: `./provision-vpn.sh -h`

```bash
# CLI mode (pass parameters directly) 
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa

# CLI mode (pass only the host, password will be prompted interactively with hidden input) 
./provision-vpn.sh -H 1.2.3.4

# Inventory mode (use pre-filled inventory.yml)
./provision-vpn.sh --use-inventory
```

### Windows (PowerShell)

To get full help message in CLI use: `Get-Help .\Provision-VPN.ps1 -Full`

```powershell
# CLI mode
.\Provision-VPN.ps1 -HostName 1.2.3.4 -PKey C:\Users\You\.ssh\id_rsa

# CLI mode (pass only the host, password will be prompted interactively with hidden input) 
.\Provision-VPN.ps1 -HostName 1.2.3.4

# Inventory mode
.\Provision-VPN.ps1 -UseInventory
```

## Configuration

### Option 1: CLI Parameters

> Supports SSH key file, password authentication or interactive password input (hidden)

Pass connection details as command-line flags:

```bash
./provision-vpn.sh -H <VPS_IP> -u <SSH_USER> -p <SSH_PORT> --pkey <PATH_TO_KEY>
```

### Option 2: Inventory File

Edit `inventory.yml` with your VPS details and use the `--use-inventory` flag:

```yaml
all:
  hosts:
    your_host:
      ansible_host: 1.2.3.4
      ansible_user: root
      ansible_port: 22
      ansible_ssh_private_key_file: /path/to/key
      ansible_ssh_pass: (leave empty or use instead of pkey file, pkey takes precedence)
```

## Parameters

### Bash Script

| Flag | Description | Required |
|------|-------------|----------|
| `-H, --host` | VPS IP/hostname | Yes (CLI mode) |
| `-u, --user` | SSH user | No (default: root) |
| `-p, --port` | SSH port | No (default: 22) |
| `--pkey` | SSH private key path | No* |
| `--pass` | SSH password | No* |
| `--use-inventory` | Use inventory.yml instead of cli arguments | No |
| `--clients-dir` | Output directory for configs | No |
| `--cleanup` | Remove temp workspace (default) | No |
| `--full-cleanup` | Remove workspace + installed packages | No |
| `--no-cleanup` | Keep workspace for debugging | No |
| `--dry-run` | Show commands without executing | No |

*You must provide either `--pkey` or `--pass`, and if none provided there will be an interactive prompt for a password with hidden input.

### PowerShell Script

Same parameters with PowerShell naming:
- `-HostName` instead of `--host`
- `-PKey` instead of `--pkey`
- `-Pass` instead of `--pass`
- `-UseInventory` instead of `--use-inventory`
- `-CleanupMode` (`Default`, `Full`, `None`)
- `-LogLevel` (`None`, `Default`, `Verbose`)

## Output

Client configuration files are saved on your local machine as:
- Linux: `./downloaded-clients/*.json` and `./downloaded-clients/*.yaml`
- Windows: `.\downloaded-clients\*.json` and `.\downloaded-clients\*.yaml`

As well as on the target VPS as:
- `/root/vpn-configs/*.json` (Amnezia) and `/root/vpn-configs/*.yaml` (Clash Verge / FlClash)

**Recommended client path:** import `clash_client_*.yaml` into Clash Verge (Windows/macOS/Linux TUN mode) or FlClash (Android).  
**Secondary (caveats):** Amnezia `client_*.json` is available but has known stability issues — Windows split-tunnel may crash the network stack; Android keepalive / background connectivity is unreliable. Use Clash Verge or FlClash instead unless you specifically need Amnezia.  
References:  
- Clash Verge: https://github.com/clash-verge-rev/clash-verge-rev  
- FlClash: https://github.com/chen08209/FlClash  
- Amnezia: https://github.com/amnezia-vpn/amnezia-client

## Advanced Configuration

For granular control over provisioning, edit `all.yml`:

```yaml
num_clients: 3                        # Number of VPN profiles to generate
reality_camouflage_domain: dl.google.com  # Domain for REALITY transport obfuscation
```

- `num_clients`: Number of client configs generated (each gets a unique UUID)
> Even a single config file allows for unlimited simultaneous connections, but several are recommended for sharing with other people and granular control.
- `reality_camouflage_domain`: Legitimate domain that REALITY redirects suspicious connections to, making VPN traffic indistinguishable from normal HTTPS

These settings are passed to the Ansible playbook during provisioning.

## Pinned Image & WARP IPv4

**Xray Docker image is pinned** to `teddysun/xray:26.6.27` (known-good).  
`:latest` is intentionally **not used** in production units — an auto-update to 26.7.11 broke VLESS+REALITY compatibility in July 2026.  
To upgrade deliberately: change `xray_docker_image` in `group_vars/all.yml` (tag or digest `sha256:…`), test, then deploy.

**WARP outbound defaults to IPv4-only** for compatibility with VPS that have no IPv6 route.  
- `warp_ipv6: false` — IPv6 WireGuard addresses are omitted from the Xray config.  
- `warp_endpoint: "162.159.192.1:2408"` — Cloudflare WARP IPv4 anycast (stable name `engage.cloudflareclient.com:2408`). Override in `group_vars/all.yml` if needed.  
- WARP is enabled via `warp_enabled: true` (requires `wgcf` 2.2.22, auto-downloaded).  
- The `warp` outbound is the default route for all traffic when enabled; `direct` is fallback.

**Secret rotation** is documented in [docs/SECRET_ROTATION.md](docs/SECRET_ROTATION.md).

## More Examples

**Custom SSH port and output directory:**
```bash
./provision-vpn.sh -H vps.example.com -p 2222 \
  --pkey ~/.ssh/id_rsa --clients-dir ~/vpn-configs
```

**Dry run (test without executing):**
```bash
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --dry-run
```

**Full cleanup (remove installed packages after run):**
```bash
./provision-vpn.sh -H 1.2.3.4 --pkey ~/.ssh/id_rsa --full-cleanup
```

## Troubleshooting

**"Command not found: ansible"**
- The script should auto-install this. If it fails, manually run:
```bash
sudo apt-get update && sudo apt-get install -y ansible
```

**"Permission denied (publickey)"**
- Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
- Test SSH manually: `ssh -i ~/.ssh/id_rsa user@host`

**"inventory.yml missing required fields"**
- Run with `--use-inventory` only after filling all fields in `inventory.yml`
- Or use CLI mode with `-H`, `--pkey`/`--pass` flags

**Line ending issues (LF vs CRLF)**
- Scripts enforce LF line endings via `.gitattributes`, so that should not be a problem
- If problems persist: `dos2unix provision-vpn.sh`, re-clone repo or create a new GitHub issue

## Contributing

Contributions welcome. Please follow conventional commits, test with a `--dry-run` and a real run with your own VPS instance (including testing the connection via Amnezia client) before submitting changes.

## Issues

Found a bug? Please open an issue with:
- Your setup (Linux/Windows, bash/PowerShell version)
- Expected vs actual behavior
- Steps to reproduce
- Relevant logs from output

Have a suggestion? Please open an issue with:
- How you currently use the project
- What would you like to introduce
- If you would like to provide and test that functionality yourself

## License

MIT

## Author

Tim Korelov  
https://github.com/lifestreamy
