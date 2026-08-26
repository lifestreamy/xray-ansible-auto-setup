> **Document:** `docs/SETUP.en.md` · **Location:** `docs/` · **Version:** v0.2 · **Last updated:** 2026-08-12
>
> [Main README](../README.en.md) — project overview and quick start

# SETUP — configuration and operation

Below are the variables and steps that actually affect server behavior. I've deployed it more than once, everything is verified.

How to prepare a VPS and a local machine; what variables exist and how they affect behavior; how to check that everything works after deployment.

The full glossary is in [`docs/GLOSSARY.en.md`](GLOSSARY.en.md).

## Configuration files

| File | What it configures | How it affects |
|---|---|---|
| `inventory.yml` (created from `inventory.yml.example`) | VPS connection: host, user, port, key or password | Only for `--use-inventory`; CLI mode builds its own inventory |
| `config/settings.yml` | All server parameters: `num_clients`, `reality_camouflage_domain`, `warp_enabled`, `xray_port`, `xray_docker_image` and others | Read on every Ansible playbook run via `vars_files` |
| `deploy.yml` | The playbook entry point | Usually left alone |

Which parameters can be passed as CLI flags — only connection parameters (`-H`, `-u`, `-p`, `--pkey`, `--pass`, `--use-inventory`, cleanup and verbosity). The rest of the configuration goes through `config/settings.yml`. The "CLI flags for all parameters" item — in [`docs/PLANNED.en.md`](PLANNED.en.md), planned after 0.3.

## About the project

This is a utility that uses Ansible to deploy an Xray VLESS + REALITY VPN server on a remote VPS. It generates client configs for Clash Verge / FlClash (Mihomo Meta YAML) and Amnezia VPN (JSON). Clash Verge and FlClash are the main recommended and tested clients. Amnezia works but isn't recommended because of instability. Platform wrappers are PowerShell and Bash scripts (PowerShell invokes Bash).

## What you need before you start

**VPS:**

- Fresh Ubuntu 20.04+ or Debian 11+.
- Root or sudo.
- Public IP.

**Local machine:**

Linux:

- Ubuntu/Debian (or any distro with `apt`).
- SSH access to the VPS.

Windows:

- WSL2 with Ubuntu/Debian (installed beforehand).
- PowerShell 5.1+ (built into Windows 10/11).

Before paying for a VPS long-term, check it with `carrox-vps-check` or `ipcheck-plus`. Details — in [`docs/TEST-VPS.en.md`](TEST-VPS.en.md).

## `config/settings.yml` variables

<details>
  <summary>All variables (for techies)</summary>

| Variable | What it does |
|---|---|
| `num_clients` | How many client configs to generate (each with its own UUID). |
| `reality_camouflage_domain` | SNI of a legitimate site for REALITY masking (default `dl.google.com`). Public parameter. |
| `xray_docker_image` | The Xray image tag. Pinned to `teddysun/xray:26.6.27`. |
| `xray_config_dir` | The state directory on the VPS (`/root/xray-config`). |
| `xray_client_configs_dir` | The generated configs directory on the VPS (`/root/vpn-configs`). |
| `xray_port` | The inbound port (default `443`). |
| `warp_enabled` | Enable the WARP outbound (`true` / `false`). |
| `warp_ipv6` | IPv6 in WireGuard (`false` — IPv4-only by default). |
| `warp_endpoint` | Cloudflare WARP endpoint (`162.159.192.1:2408`). |
| `warp_mtu` | WireGuard MTU (`1420`). |
| `warp_wgcf_version` | wgcf version (`2.2.22`). |
| `warp_wgcf_url` | URL for downloading wgcf. |
| `xray_backup_enabled` | Timestamped backups before overwriting (`true`). |
| `xray_reality_rotate` | Full REALITY rotation. Default `false`. Details — in [`docs/ROTATION.en.md`](ROTATION.en.md). |

</details>

## WARP in detail

`warp_enabled: true` adds an extra outgoing tunnel through Cloudflare WARP to Xray. This hides your VPS IP from visited sites — they'll see the Cloudflare IP instead of yours.

**IPv4-only by default.** The `warp_ipv6: false` parameter excludes the IPv6 address from the WireGuard interface. This is for compatibility with VPSes without an IPv6 route. In this mode `allowedIPs` and `domainStrategy` remain, but the actual tunnel goes over IPv4 only. If you have working IPv6, switch to `true`.

**Endpoint.** Default `162.159.192.1:2408` — the Cloudflare WARP IPv4 anycast. The stable name is `engage.cloudflareclient.com:2408`. Override in `config/settings.yml` if needed.

**Requirements.** `wgcf` 2.2.22. The role downloads the binary itself when `warp_enabled: true`. Persistent credentials are `wgcf-account.toml` and `wgcf-profile.conf` in `/root/xray-config/`.

**Egress check.** Check from outside the VPS, through a real VPN client, not via `curl` from inside the Xray container. From the device where the VPN client runs:

```bash
curl -4 https://ifconfig.io   # should return the Cloudflare IP (or VPS IP if WARP is off)
curl -4 https://cloudflare.com/cdn-cgi/trace   # alternative, look for colo= and ip=
```

WARP rotation details — in [`docs/ROTATION.en.md`](ROTATION.en.md), section §4.

## Post-deployment checks

After any run (with or without rotation) do a manual check.

Check that the right Xray image is running (should return `teddysun/xray:26.6.27` or the current `xray_docker_image` value):

```bash
docker inspect xray --format '{{ .Config.Image }}'   # prints the image tag
```

Check that the Xray journal has no REALITY handshake errors:

```bash
journalctl -u xray --no-pager -n 30 | grep -iE 'error|fail|panic'   # grep filters only problem lines
```

Check that the Xray port (`xray_port`, default `443`) is listening on the VPS:

```bash
nc -zv <VPS_IP> 443   # replace <VPS_IP> with yours; should return succeeded
```

Connect with at least one real client (Clash Verge / FlClash / Amnezia) and verify traffic goes through it.

The role's built-in checks cover only the pinned image, the listening port and obvious journal errors. They don't replace the manual check above.

## Adding more clients without rotation

To add a new client config without touching existing keys — increase `num_clients` in `config/settings.yml` and run the playbook. New UUIDs will be added to `reality-state.json`, new configs will appear in `/root/vpn-configs/` on the VPS and in `./downloaded-clients/` locally. Existing clients keep working.

## License

AGPL-3.0 with an additional commercial-use restriction. Free for personal use and non-commercial distribution. Commercial use — only with the author's written permission: **tim.korelov@yandex.com**.

Full text — in [`LICENSE`](../LICENSE) (English). A short summary in Russian — in [`LICENSE.ru.md`](../LICENSE.ru.md).
