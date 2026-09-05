> **Document:** `docs/PLANNED.en.md` · **Location:** `docs/` · **Version:** v0.3 · **Last updated:** 2026-09-05
>
> [Main README](../README.en.md) — project overview and quick start

# What's planned, in progress, and done

Deadlines are rough targets, not promises. The order can change.

## Done in v0.3 (2026-09-05)

- All role configuration (the set of files that deploys Xray on the server) lives in one file: `config/settings.yml`.
- The primary CLI client `xrayvpn` (Python): remote mode over SSH and local mode; parameters go
  through CLI flags, no hand-editing of yaml files.
- GitHub Actions CI: molecule matrix on ubuntu 22.04 / 24.04 / debian 12 plus a full host run
  with the mihomo-client e2e (ufw is exercised there).
- Runtimes: `native` (default), `docker`, `podman`. Container systemd units use `--network host`.
- `xray.service` is enabled on deploy; `ufw` and `python3-venv` are auto-installed where needed.
- Readable `inventory.yml` errors with a hint on how to create the file from the template.
- Release policy (`docs/RELEASE.en.md`), CHANGELOG (RU/EN), docs brought to one rhythm.

## High priority

- Promote v0.3 to stable — per the criteria in `docs/RELEASE.en.md` (14+ days on the personal VPS without fixes).

## Medium priority

- **[Client]** — our own visual client: cross-platform, simple deployment and management. Once
  there are binaries: self-update via releases (the common scheme — a `latest.json` manifest with
  per-platform urls and signatures) and installing from package managers (winget / choco / PyPI).
  Target: post-0.3.
- **[Infrastructure]** — compare runtimes by footprint and latency (podman vs native); for now
  this is a research item.
- **[WARP]** — think through scenarios: multiple outbounds, endpoint rotation. Target: none.

## Low priority

- (free for now — will appear along the way)
