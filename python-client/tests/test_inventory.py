"""Tests for core/inventory.py: local and server inventory rendering."""

from __future__ import annotations

import yaml

from xrayvpn.core.inventory import build_inventory, write_inventory


def test_local_inventory_connection(tmp_path) -> None:
    content = build_inventory({"xray_runtime": "native"}, connection="local")
    data = yaml.safe_load(content)
    host = data["all"]["hosts"]["vpn"]
    assert host["ansible_connection"] == "local"
    assert "ansible_python_interpreter" not in host
    assert data["all"]["vars"] == {"xray_runtime": "native"}


def test_server_inventory_interpreter() -> None:
    content = build_inventory(
        {"warp_enabled": False},
        python_interpreter="/opt/xrayvpn-venv/bin/python",
    )
    data = yaml.safe_load(content)
    host = data["all"]["hosts"]["vpn"]
    assert host["ansible_python_interpreter"] == "/opt/xrayvpn-venv/bin/python"


def test_write_inventory_file(tmp_path) -> None:
    path = write_inventory(tmp_path, build_inventory({}, connection="local"))
    assert path.name == "inventory.yml"
    assert "hosts" in path.read_text(encoding="utf-8")