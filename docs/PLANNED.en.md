> **Document:** `docs/PLANNED.en.md` · **Location:** `docs/` · **Version:** v0.2 · **Last updated:** 2026-08-12
>
> [Main README](../README.en.md) — project overview and quick start

# What's planned, in progress, and done

Any deadlines are just rough targets, not promises. The order can change.

## High priority

- **[Config]** — refactor: merge `roles/xray_vpn/defaults/main.yml`, `group_vars/all.yml` and `inventory.yml` into one directory (`config/`), remove default duplication. Right now 8 variables from `defaults/main.yml` are duplicated in `group_vars/all.yml` with the same values. Target: 0.4.
- **[Tests]** — deployment tests: local run on a computer after changes, without touching a personal VPS. They verify that the server deploys, the client connects and traffic goes out. Idea: the Ansible role against a local container (molecule + docker), smoke checks with a real client inside the test. Target: after 0.3.

## Medium priority

- **[Infrastructure]** — move off Docker to Podman or other options for better performance, lower ping, etc. Target: none yet — research item.
- **[Client]** — a visual client of our own: cross-platform, with a simple interface for deployment and management. Target: after 0.3.
- **[Scripts]** — rewrite the wrappers in universal Python (works on all platforms). The old `provision-vpn.sh` and `Provision-VPN.ps1` are marked deprecated: they stay working for compatibility but aren't developed. Target: after 0.3.
- **[Scripts]** — all launch parameters as CLI flags: `warp_enabled`, `num_clients`, `xray_port`, `reality_camouflage_domain` and the rest — so you don't edit yml files by hand. Target: after 0.3.

## Low priority

- (free for now — will appear along the way)
