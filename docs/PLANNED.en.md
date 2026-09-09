> **Document:** `docs/PLANNED.en.md` · **Location:** `docs/` · **Version:** v0.4.0 · **Last updated:** 2026-09-09
>
> [Main README](../README.en.md) — project overview and quick start

# What's planned, in progress, and done

Deadlines are rough targets, not promises. The order can change.

## Done in v0.4.0 (2026-09-09)

- Running the client with no arguments now provisions a remote VPS by default (it asks for the IP
  and the password); local mode requires the explicit `--execution local`.
- Low-memory protection for weak VPS: with < 1024 MB RAM and no swap the client offers to create
  a 1 GB swapfile (an explicit prompt; an existing swap configuration is never touched).
- Fully Russian client interface: the `--ru` flag (prompts, messages, errors, `--help`) and the
  `XRAYVPN_LANG` environment variable; double-click launchers on Windows — English and Russian
  (`xrayvpn-deploy.pyw` / `xrayvpn-deploy-ru.pyw`).
- The `xrayvpn` command installs onto PATH: `uv tool install --editable python-client`.
- Rotation flags in the bash/PowerShell wrappers: `--rotate`/`--no-rotate` and `-Rotate`/`-NoRotate`.
- The role no longer installs `ufw`: the allow rule is added only if `ufw` already exists
  (variable and flag renamed to `xray_manage_ufw` / `--manage-ufw`).
- The experimental `podman` runtime removed (it never left experimental).
- CI: client tests additionally on Windows and macOS; uv pinned to an exact version.
- Release policy: three-component versions, one release per version, stable criteria without
  a calendar soak (CI coverage of client scenarios + a manual click-through cheatsheet).

## Done in v0.3 (2026-09-05)

- All role configuration (the set of files that deploys Xray on the server) lives in one file: `config/settings.yml`.
- The primary CLI client `xrayvpn` (Python): remote mode over SSH and local mode; parameters go
  through CLI flags, no hand-editing of yaml files.
- GitHub Actions CI: molecule matrix on ubuntu 22.04 / 24.04 / debian 12 plus a full host run
  with the mihomo-client e2e (ufw is exercised there).
- Runtimes: `native` (default), `docker`. Container systemd units use `--network host`.
- `xray.service` is enabled on deploy; `python3-venv` and `ufw` were auto-installed where needed
  (the `ufw` behavior changed in v0.4.0).
- Readable `inventory.yml` errors with a hint on how to create the file from the template.
- Release policy (`docs/RELEASE.en.md`), CHANGELOG (RU/EN), docs brought to one rhythm.

## High priority

- Promote v0.4.0 to stable — per the criteria in `docs/RELEASE.en.md`: CI coverage of the client
  scenarios (python + bash + PowerShell × Ubuntu/Windows/macOS) and a manual click-through of all
  scenarios on a real VPS following the testing cheatsheet; no calendar soak.

## Medium priority

- **[Client]** — our own visual client: cross-platform, simple deployment and management. Once
  there are binaries: self-update via releases (the common scheme — a `latest.json` manifest with
  per-platform urls and signatures) and installing from package managers (winget / choco / PyPI);
  the package name will be chosen before publishing — target: v0.4.1.
- **[WARP]** — think through scenarios: multiple outbounds, endpoint rotation. Target: none.

## Low priority

- (free for now — will appear along the way)
