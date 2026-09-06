"""Inventory generation (PyYAML, no regex).

One builder serves both execution modes:
- local:  `ansible_connection=local` (the playbook runs on the current host);
- remote: generated *on the server* with `ansible_connection=local` and the
  bootstrap venv's interpreter (inventory.yml is never uploaded — ADR-008).

The generated file uses its own gitignored name so the user's personal
`inventory.yml` is never touched or overwritten.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

INVENTORY_FILE = ".xrayvpn-inventory.yml"


def build_inventory(
    vars: dict[str, Any],
    *,
    connection: str = "local",
    host: str = "vpn",
    python_interpreter: str | None = None,
) -> str:
    """Render a one-host inventory YAML. `python_interpreter=None` lets Ansible discover it."""
    host_vars: dict[str, Any] = {"ansible_connection": connection}
    if python_interpreter is not None:
        host_vars["ansible_python_interpreter"] = python_interpreter
    body: dict[str, Any] = {"all": {"hosts": {host: host_vars}, "vars": vars}}
    return yaml.safe_dump(body, sort_keys=False, allow_unicode=True)


def write_inventory(repo_root: Path, content: str) -> Path:
    """Persist inventory content at the repo root (file is gitignored)."""
    path = repo_root / INVENTORY_FILE
    path.write_text(content, encoding="utf-8")
    return path


CONNECTION_KEYS = (
    "ansible_host",
    "ansible_user",
    "ansible_port",
    "ansible_ssh_private_key_file",
    "ansible_ssh_pass",
)

REQUIRED_CONNECTION_KEYS = ("ansible_host", "ansible_user", "ansible_port")


def validate_connection(connection: dict[str, str]) -> list[str]:
    """Return human-readable problems with parsed connection params (empty = OK).

    Missing auth is NOT a problem here: the CLI falls back to a hidden password
    prompt (parity with the pre-validation flow).
    """
    problems = [
        f"{key} is not set"
        for key in REQUIRED_CONNECTION_KEYS
        if not connection.get(key)
    ]
    port = connection.get("ansible_port")
    if port and not port.isdigit():
        problems.append(f"ansible_port must be numeric, got: {port!r}")
    has_key = bool(connection.get("ansible_ssh_private_key_file"))
    has_pass = bool(connection.get("ansible_ssh_pass"))
    if has_key and has_pass:
        problems.append(
            "both ansible_ssh_private_key_file and ansible_ssh_pass are set; "
            "leave only one"
        )
    return problems


def parse_user_inventory(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Read the user's personal inventory.yml (read-only; never written).

    Returns (connection params, extra vars). Connection keys are the
    ansible_* connection fields; every other host/all var is treated as a
    playbook extra var.
    """
    path = repo_root / "inventory.yml"
    if not path.is_file():
        example = repo_root / "inventory.yml.example"
        raise RuntimeError(
            f"inventory file not found: {path}\n"
            "create it from the template and fill in ansible_host, ansible_user, "
            "ansible_port and ONE auth method:\n"
            f"  cp {example} {path}\n"
            f"  (Windows PowerShell: Copy-Item {example.name} {path.name})"
        )
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"inventory file must contain a YAML mapping: {path}")

    connection: dict[str, str] = {}
    extra_vars: dict[str, Any] = {}
    all_section = data.get("all", {})
    if isinstance(all_section, dict):
        raw_vars = all_section.get("vars", {})
        if isinstance(raw_vars, dict):
            extra_vars.update(raw_vars)
        hosts = all_section.get("hosts", {})
        for host_vars in hosts.values():
            if not isinstance(host_vars, dict):
                continue
            for key, value in host_vars.items():
                if key in CONNECTION_KEYS:
                    # empty YAML scalars (None) stay unset — never str(None)="None"
                    if value is not None and key not in connection:
                        connection[key] = str(value)
                elif not key.startswith("ansible_"):
                    extra_vars[key] = value
    return connection, extra_vars