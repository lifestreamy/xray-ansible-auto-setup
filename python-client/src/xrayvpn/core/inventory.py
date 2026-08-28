"""Inventory generation (PyYAML, no regex).

One builder serves both execution modes:
- local:  `ansible_connection=local` (the playbook runs on the current host);
- remote: generated *on the server* with `ansible_connection=local` and the
  bootstrap venv's interpreter (inventory.yml is never uploaded — ADR-008).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

INVENTORY_FILE = "inventory.yml"


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