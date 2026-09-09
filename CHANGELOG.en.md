# Changelog

Version history. Русская версия: [CHANGELOG.md](CHANGELOG.md).
Release policy and release statuses — [docs/RELEASE.en.md](docs/RELEASE.en.md).

Format:

- Newest versions first; one section per release: `## [vX.Y] — YYYY-MM-DD`.
- Inside a section — categories: **Added**, **Changed**, **Fixed**, **Removed**.
- Each release section carries a `Status:` line (`experimental`; after promotion — `stable since YYYY-MM-DD`).
- Entries are built from commit messages and land in the release commit; no auto-bump.
- The RU/EN pair is updated in the same commit; section structure is mirrored.

## [Unreleased]

### Added
- `--ru` (global and on `deploy`): Russian CLI output — prompts, messages, errors
  (help texts stay English).

### Changed
- **Breaking**: `xrayvpn deploy` now defaults to `--execution remote` (was `local`): a no-argument
  run provisions a remote VPS (asks for the IP and the password); local mode requires the explicit
  `--execution local`.
- Remote deploy: low-memory guard — with < 1024 MB RAM and no active swap the client offers to
  create a 1 GB `/swapfile` (explicit opt-in prompt; an existing swap/fstab configuration is never
  touched).
- The role no longer installs `ufw`: the allow rule for `xray_port`/tcp is added only when `ufw`
  already exists on the server. The `xray_manage_firewall` variable and CLI flag renamed to
  `xray_manage_ufw` / `--manage-ufw/--no-ufw`.

### Removed
- The `podman` runtime (experimental stub, never left experimental; not covered by molecule
  tests). Supported runtimes: `native` (default) and `docker`.

## v0.3 — 2026-09-05

Status: experimental (promotion criteria — `docs/RELEASE.en.md`).

### Added
- The primary CLI client `xrayvpn` (Python): remote mode over SSH and a local mode, common
  parameters as flags.
- GitHub Actions CI: `molecule` workflow — syntax check, molecule matrix on ubuntu 22.04/24.04 and
  debian 12, a full host run with the firewall and a mihomo-client e2e; `python-client` workflow —
  CLI tests and lint.
- Manual check runbook — `docs/TEST-LOCAL.en.md`.
- Release policy — `docs/RELEASE.en.md`: experimental/stable statuses, tag scheme, release
  sequence. The CHANGELOG pair (this file plus `CHANGELOG.md`).
- Hints for clients when `inventory.yml` is missing or incomplete.
- Enabling `xray.service` at boot and auto-install of `ufw` / `python3-venv` during deploy.

### Changed
- All role variables live in one file, `config/settings.yml`; `group_vars/` and role defaults
  are gone.
- Runtime choice: `native` (default), `docker`, `podman` (experimental).
- Docker and podman units run with `--network host`, no extra NAT hop.
- Repository layout: `shell-clients/`, `python-client/`, `scripts/`, `config/`; contributor
  tooling separated from client wrappers.
- README quick start: three run paths (the clients and bare Ansible) with direct file links,
  command details in collapsible blocks.

### Fixed
- Readable inventory error messages; `--use-inventory` parsing in the shell clients was broken
  since v0.2.

## v0.2 — 2026-08-03

First publicly documented release (predates the current release policy; tagged `v0.2_release`).
Detailed change history starts with v0.3.
