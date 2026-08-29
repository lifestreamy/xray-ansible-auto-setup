"""Tests for core/inventory.py: local and server inventory rendering."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from xrayvpn.core.inventory import (
    build_inventory,
    parse_user_inventory,
    write_inventory,
)


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
    assert path.name == ".xrayvpn-inventory.yml"
    assert "hosts" in path.read_text(encoding="utf-8")


def test_parse_user_inventory_split(tmp_path: Path) -> None:
    (tmp_path / "inventory.yml").write_text(
        "all:\n"
        "  hosts:\n"
        "    my_vps:\n"
        "      ansible_host: 1.2.3.4\n"
        "      ansible_user: root\n"
        "      ansible_ssh_private_key_file: ~/.ssh/id_rsa\n"
        "      xray_port: 8443\n"
        "  vars:\n"
        "    num_clients: 2\n",
        encoding="utf-8",
    )
    connection, extra_vars = parse_user_inventory(tmp_path)
    assert connection == {
        "ansible_host": "1.2.3.4",
        "ansible_user": "root",
        "ansible_ssh_private_key_file": "~/.ssh/id_rsa",
    }
    assert extra_vars == {"xray_port": 8443, "num_clients": 2}


def test_parse_user_inventory_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not found"):
        parse_user_inventory(tmp_path)