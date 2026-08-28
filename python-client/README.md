# python-client

Python client for provisioning the Xray VPN server.

One client, two execution modes:

- `local` — run the playbook against the current machine (Linux: direct call;
  Windows: via the WSL bridge);
- `remote` — bootstrap and run on a remote VPS over SSH (SFTP upload, no
  GitHub dependency).

## Install / run

```bash
uv sync                 # create .venv and install (inside python-client/)
uv run xrayvpn --help   # or: python3 -m xrayvpn
```

## Layout

- `src/xrayvpn/` — application package (`cli/`, `core/`, `core/execution/`,
  `core/transport/`);
- `tests/` — pytest suite.

The repo zones next to this package: `shell-clients/` (standalone Bash /
PowerShell clients) and `scripts/` (contributor tooling).