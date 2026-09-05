"""Tests for core/execution/local.py: command and WSL-script construction, venv preflight."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from xrayvpn.core import wsl
from xrayvpn.core.execution.base import DeployRequest
from xrayvpn.core.execution.local import LocalExecutor


def _request(tmp_path: Path, **kwargs) -> DeployRequest:
    return DeployRequest(repo_root=tmp_path, **kwargs)


def test_build_command_direct(tmp_path: Path) -> None:
    executor = LocalExecutor()
    cmd = executor.build_command(
        _request(tmp_path, overrides={"warp_enabled": False, "num_clients": 3})
    )
    assert cmd[0] == "~/xray-venv/bin/ansible-playbook"
    assert "deploy.yml" in cmd
    assert "-i" in cmd
    assert cmd[cmd.index("-i") + 1] == str(tmp_path / ".xrayvpn-inventory.yml")
    json_var = cmd[cmd.index("-e") + 1]
    assert json_var == '{"num_clients": 3, "warp_enabled": false}'


def test_build_command_custom_inventory_wins(tmp_path: Path) -> None:
    executor = LocalExecutor()
    custom = tmp_path / "custom-inv.yml"
    cmd = executor.build_command(_request(tmp_path, inventory_path=custom))
    assert cmd[cmd.index("-i") + 1] == str(custom)


def test_build_command_verbosity_and_check(tmp_path: Path) -> None:
    executor = LocalExecutor()
    cmd = executor.build_command(
        _request(tmp_path, verbosity=4, debug=True, dry_run=True)
    )
    assert "-vvvv" in cmd
    pairs = [cmd[i : i + 2] for i in range(len(cmd) - 1)]
    assert ["-e", "xray_debug=true"] in pairs
    assert "--check" in cmd


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="WSL bridge exists only for Windows hosts (Linux runs natively)",
)
def test_build_wsl_script_resolves_home_and_mnt_path(tmp_path: Path) -> None:
    executor = LocalExecutor()
    script = executor.build_wsl_script(
        _request(tmp_path, overrides={"xray_runtime": "native"}),
        wsl_home="/home/tim",
    )
    assert script.startswith("cd /mnt/")
    assert "/home/tim/xray-venv/bin/ansible-playbook" in script
    assert "'{\"xray_runtime\": \"native\"}'" in script
    assert "ANSIBLE_FORCE_COLOR=1" in script


def test_build_wsl_script_absolute_venv(tmp_path: Path) -> None:
    executor = LocalExecutor(wsl_venv="/opt/venv")
    script = executor.build_wsl_script(_request(tmp_path), wsl_home="/home/tim")
    assert "/opt/venv/bin/ansible-playbook" in script


def test_venv_binary_resolution() -> None:
    assert LocalExecutor().venv_binary() == "~/xray-venv/bin/ansible-playbook"
    assert (
        LocalExecutor().venv_binary(wsl_home="/home/tim")
        == "/home/tim/xray-venv/bin/ansible-playbook"
    )
    assert LocalExecutor(wsl_venv="/opt/venv").venv_binary() == "/opt/venv/bin/ansible-playbook"


def test_deploy_linux_missing_venv_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wsl, "is_windows", lambda: False)
    executor = LocalExecutor(wsl_venv=str(tmp_path / "novenv"))
    with pytest.raises(RuntimeError, match="setup_test_env"):
        executor.deploy(_request(tmp_path))


def test_deploy_wsl_missing_venv_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wsl, "is_windows", lambda: True)
    monkeypatch.setattr(wsl, "wsl_available", lambda: True)
    monkeypatch.setattr(wsl, "wsl_home", lambda distro=None: "/home/tim")
    monkeypatch.setattr(wsl, "path_exists", lambda path, *, distro=None: False)
    executor = LocalExecutor()
    with pytest.raises(RuntimeError, match="not found in WSL"):
        executor.deploy(_request(tmp_path))


def test_deploy_wsl_happy_path_runs_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(wsl, "is_windows", lambda: True)
    monkeypatch.setattr(wsl, "wsl_available", lambda: True)
    monkeypatch.setattr(wsl, "wsl_home", lambda distro=None: "/home/tim")
    monkeypatch.setattr(wsl, "path_exists", lambda path, *, distro=None: True)
    monkeypatch.setattr(
        wsl, "run_script", lambda script, *, distro=None: calls.append(script) or 0
    )
    executor = LocalExecutor()
    assert executor.deploy(_request(tmp_path)) == 0
    assert any("/home/tim/xray-venv/bin/ansible-playbook" in s for s in calls)