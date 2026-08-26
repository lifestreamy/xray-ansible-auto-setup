# `config/`

Settings for the `xray_vpn` role. One file — one source of truth.

## Contents

- `settings.yml` — all parameters Ansible needs at deploy time. Loaded from `deploy.yml` via `vars_files`. These values used to live in two places (`group_vars/all.yml` and `roles/xray_vpn/defaults/main.yml`) — now they are in a single file.

## Why

A subset of variables was duplicated between `group_vars/all.yml` and `roles/xray_vpn/defaults/main.yml`. The conflict was settled by Ansible precedence (group_vars override role defaults), but it caused errors: edit one place, forget the other — an hour of debugging.

Now everything lives in `settings.yml`. The role has no defaults of its own; `group_vars/` is gone. One file, one source.

## Overriding

Personal values for a specific VPS (for example, `num_clients` or a different `reality_camouflage_domain`) are set in `inventory.yml` (not committed, listed in `.gitignore`). Or via CLI flags when they exist.

For the molecule scenario, values live in `molecule/default/molecule.yml` — the `provisioner.inventory.group_vars.all` block. That is a test-only path; production never uses it.

## Notes

- Do not remove the incident comment (2026-07-28) next to `xray_docker_image` about image pinning.