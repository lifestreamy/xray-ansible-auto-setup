# `python-client/`

The primary `xrayvpn` client (Python) — deploy, update and rotate an Xray server.
Works the same on Windows, Linux and macOS; two execution models behind one CLI.

## Install and run

Requires [uv](https://docs.astral.sh/uv/) (or Python 3.12+):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # Windows
```

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh                                       # Linux/macOS
```

From the repository root:

```bash
uv run --project python-client xrayvpn --help
```

Inside `python-client/` (after `uv sync`) both `uv run xrayvpn ...` and `python -m xrayvpn` work.
On Windows you can skip flags entirely: double-clicking `xrayvpn-deploy.pyw` opens a console and
runs a local deploy (the hyphen in the name is mandatory — a plain `xrayvpn.pyw` next to the
package would hijack `import xrayvpn` on Windows).

## Two execution models

- **remote** (`--execution remote`) — the client bootstraps the VPS over SSH itself:
  environment setup, repo uploaded as a tarball (the server never needs GitHub), the playbook,
  then it fetches the generated client configs.
- **local** (`--execution local`) — the playbook runs on this machine: directly on Linux,
  through WSL on Windows (the client finds/creates `uv` and a venv inside the distro;
  default venv `~/xray-venv`).
- Without `--execution` the CLI asks in the terminal (default: local).

## Examples

```bash
# VPS by IP: the password is prompted with hidden input (or pass --pkey ~/.ssh/id_ed25519)
uv run --project python-client xrayvpn deploy --execution remote --host 1.2.3.4

# connection parameters from the personal inventory.yml
uv run --project python-client xrayvpn deploy --execution remote --use-inventory

# local run, no WARP, no forced rotation
uv run --project python-client xrayvpn deploy --execution local --no-warp --no-rotate

# the remote deploy plan without connecting anywhere
uv run --project python-client xrayvpn deploy --execution remote --host 1.2.3.4 --dry-run
```

## `deploy` flags

- Mode: `--execution local|remote`.
- Server overrides (otherwise taken from `config/settings.yml`): `--runtime native|docker|podman`,
  `--xray-port`, `--num-clients`, `--camouflage-domain`, `--warp/--no-warp`,
  `--rotate/--no-rotate` (regenerate the REALITY key and UUIDs / keep them),
  `--manage-firewall/--no-firewall`.
- Inventory: `--inventory PATH` — local only, an existing file instead of the generated one;
  `--use-inventory` — remote only, reads connection vars from the personal `inventory.yml`
  (overrides the host/key flags with a warning).
- Connection (remote): `--host`/`-H`, `--user`/`-u` (default `root`), `--port`/`-p` (default 22),
  `--pkey FILE` (preferred), `--pass TEXT` (plain password, worse than a key; omit both and
  it prompts, hidden).
- Output: `--clients-dir PATH` — where client configs are saved
  (default `<repo>/downloaded-clients/`, fetched from the server's `/root/vpn-configs`).
- Server-side cleanup (remote): by default the staging dir is removed, the venv stays;
  `--full-cleanup` removes the venv too, `--no-cleanup` leaves everything.
- Diagnostics: `--dry-run` (local: ansible `--check`; remote: plan without connecting),
  `--debug` / `--verbose` (Ansible -vvv/-vvvv; mutually exclusive, as are `--pkey` with `--pass`).

Full list: `xrayvpn deploy --help`.

## Layout

- `src/xrayvpn/` — the package (`cli/`, `core/`, `core/execution/`, `core/transport/`);
- `tests/` — pytest suite (the `python-client` CI leg runs it plus ruff; there is also a static
  contract test `xrayvpn-deploy.pyw` ↔ CLI);
- sibling repo zones: `shell-clients/` (Bash/PowerShell, maintained, not developed) and
  `scripts/` (contributor tooling).

Server configuration — [../docs/SETUP.en.md](../docs/SETUP.en.md), key rotation —
[../docs/ROTATION.en.md](../docs/ROTATION.en.md).
