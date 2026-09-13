"""`xrayvpn service` — whitelisted commands, conn resolution and CLI guards."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Self

import pytest
from typer.testing import CliRunner

import xrayvpn.cli.service as service_mod
from xrayvpn import i18n
from xrayvpn.cli.main import app
from xrayvpn.cli.repl import help_text
from xrayvpn.core.conn import ConnResolveError, resolve_connection
from xrayvpn.core.inventory import parse_user_inventory
from xrayvpn.core.runtime_paths import RunRoots
from xrayvpn.core.service_actions import (
    logs_journal_command,
    reboot_command,
    restart_commands,
    status_commands,
)
from xrayvpn.core.transport.remote import CommandResult

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_i18n():
    i18n.set_ru(False)
    yield
    i18n.set_ru(False)


def _output(result) -> str:
    text = result.output or ""
    stderr = getattr(result, "stderr", "") or ""
    return text + stderr


class FakeRemote:
    """Scripted Remote: returns a canned CommandResult per executed prefix."""

    calls: ClassVar[list[str]] = []
    responses: ClassVar[dict[str, str]] = {}

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        return None

    def run(self, command, *, sudo=False, warn=True, env=None) -> CommandResult:
        FakeRemote.calls.append(command)
        for prefix, out in FakeRemote.responses.items():
            if command.startswith(prefix):
                return CommandResult(return_code=0, stdout=out)
        return CommandResult(return_code=0, stdout="")


def _stub_transport(monkeypatch, tmp_path: Path) -> None:
    FakeRemote.calls = []
    FakeRemote.responses = {
        "systemctl is-active xray": "active\n",
        "systemctl show xray -p NRestarts": "NRestarts=0\nActiveEnterTimestamp=Sat 2026-09-13 00:00:00 UTC\nSubState=running\n",
        "sudo -n journalctl -u xray --since '-30m' -o cat": "3\n",
        "sudo -n journalctl -u xray -u xray-obs-snapshot": "2026-09-13T00:00:00Z xray[1]: sample journal line\n",
    }
    monkeypatch.setattr(service_mod, "FabricRemote", FakeRemote)
    monkeypatch.setattr(
        service_mod,
        "_roots",
        lambda: RunRoots(repo=tmp_path, workspace=tmp_path, payload=tmp_path),
    )


def _key(tmp_path: Path) -> Path:
    key = tmp_path / "id_ed25519"
    key.write_text("fake", encoding="utf-8")
    return key


# --- builders: exact whitelist strings ---

def test_status_commands_are_exact() -> None:
    cmds = status_commands(443, 10820, 30)
    assert cmds == [
        "systemctl is-active xray",
        "systemctl show xray -p NRestarts -p ActiveEnterTimestamp -p SubState",
        "sudo -n journalctl -u xray --since '-30m' -o cat | grep -Ec 'wireguard|outbound' || true",
        "sudo -n journalctl -u xray -u xray-obs-snapshot -u xray-watchdog --since '-30m' -o short-iso --no-pager | tail -n 60",
        "sudo -n ss -tulpn '( sport = :443 or sport = :10820 or sport = :22 )'",
        "free -m",
    ]


def test_restart_and_reboot_commands() -> None:
    assert restart_commands() == [
        "sudo -n systemctl reset-failed xray",
        "sudo -n systemctl restart xray",
        "systemctl is-active xray",
    ]
    assert reboot_command() == "sudo -n systemctl reboot"


def test_logs_command_streams_over_ssh() -> None:
    cmd = logs_journal_command("24h")
    assert cmd == (
        'sudo -n journalctl -u xray -u xray-obs-snapshot -u xray-watchdog '
        '--since "-24h" -o short-iso --no-pager'
    )
    assert ">" not in cmd and "; " not in cmd and "&&" not in cmd


# --- conn.resolve_connection ---

def test_conn_explicit_pkey(tmp_path: Path) -> None:
    key = _key(tmp_path)
    conn = resolve_connection(
        workspace=tmp_path, example_dir=tmp_path, host=" 1.2.3.4 ", pkey=key, no_interactive=True
    )
    assert conn.host == "1.2.3.4" and conn.user == "root" and conn.port == 22
    assert conn.pkey == str(key) and conn.password is None


def test_conn_requires_host(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ConnResolveError, match="VPS host required"):
        resolve_connection(workspace=tmp_path, example_dir=tmp_path, no_interactive=True)


def test_conn_mutex_and_missing_key(tmp_path: Path) -> None:
    import pytest

    key = _key(tmp_path)
    with pytest.raises(ConnResolveError, match="private key and a password"):
        resolve_connection(
            workspace=tmp_path, example_dir=tmp_path, host="h", pkey=key, password="x",
            no_interactive=True,
        )
    with pytest.raises(ConnResolveError, match="private key not found"):
        resolve_connection(
            workspace=tmp_path, example_dir=tmp_path, host="h", pkey=tmp_path / "nope",
            no_interactive=True,
        )


def test_conn_password_prompt_or_error(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ConnResolveError, match="SSH auth required"):
        resolve_connection(workspace=tmp_path, example_dir=tmp_path, host="h", no_interactive=True)
    conn = resolve_connection(
        workspace=tmp_path, example_dir=tmp_path, host="h",
        ask_password=lambda _q: "s3cret",
    )
    assert conn.password == "s3cret"


def _write_inventory(workspace: Path, hosts: list[tuple[str, str]]) -> None:
    lines = ["all:", "  hosts:"]
    for name, host in hosts:
        lines += [
            f"    {name}:",
            f"      ansible_host: {host}",
            "      ansible_user: root",
            "      ansible_port: 22",
            "      ansible_ssh_private_key_file: ''",
        ]
    (workspace / "inventory.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_conn_single_host_inventory(tmp_path: Path) -> None:

    _write_inventory(tmp_path, [("vpn", "5.6.7.8")])
    conn = resolve_connection(
        workspace=tmp_path, example_dir=tmp_path, use_inventory=True,
        ask_password=lambda _q: "pw",
    )
    assert conn.host == "5.6.7.8" and conn.password == "pw"


def test_conn_multi_host_inventory_rejected(tmp_path: Path) -> None:
    import pytest

    _write_inventory(tmp_path, [("vpn", "5.6.7.8"), ("second", "9.9.9.9")])
    with pytest.raises(ConnResolveError, match="multiple hosts"):
        resolve_connection(workspace=tmp_path, example_dir=tmp_path, use_inventory=True)


def test_conn_missing_inventory_is_clean_error(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ConnResolveError, match="inventory file not found"):
        resolve_connection(workspace=tmp_path, example_dir=tmp_path, use_inventory=True)


def test_conn_empty_string_pkey_parity(tmp_path: Path) -> None:
    lines = [
        "all:",
        "  hosts:",
        "    vpn:",
        "      ansible_host: 5.6.7.8",
        "      ansible_user: root",
        "      ansible_port: 22",
        '      ansible_ssh_private_key_file: ""',
        "      ansible_ssh_pass: secret",
    ]
    (tmp_path / "inventory.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    connection, _extra = parse_user_inventory(tmp_path, example_dir=tmp_path)
    assert "ansible_ssh_private_key_file" not in connection
    conn = resolve_connection(
        workspace=tmp_path, example_dir=tmp_path, use_inventory=True, no_interactive=True
    )
    assert conn.pkey is None and conn.password == "secret"


# --- CLI wiring ---

def test_service_status_end_to_end(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    result = runner.invoke(
        app, ["service", "status", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"]
    )
    assert result.exit_code == 0, _output(result)
    out = _output(result)
    assert "service xray@1.2.3.4" in out and "ошибок" not in out
    assert "outbound errors in the last 30 min: 3" in out
    assert any(c.startswith("sudo -n ss -tulpn") for c in FakeRemote.calls)


def test_service_status_ru(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    result = runner.invoke(
        app,
        ["service", "status", "--ru", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"],
    )
    out = _output(result)
    assert "сервис xray@1.2.3.4" in out and "ошибок исходящего" in out


def test_reboot_requires_yes(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    result = runner.invoke(
        app, ["service", "reboot", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"]
    )
    assert result.exit_code == 2
    assert "--yes" in _output(result)
    assert not any(c.startswith("sudo -n systemctl reboot") for c in FakeRemote.calls)

    result = runner.invoke(
        app,
        ["service", "reboot", "--yes", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"],
    )
    assert result.exit_code == 0, _output(result)
    assert "sudo -n systemctl reboot" in FakeRemote.calls
    assert "[ok] host 1.2.3.4 is rebooting" in _output(result)


def test_reboot_error_ru(tmp_path) -> None:
    key = _key(tmp_path)
    result = runner.invoke(
        app, ["service", "reboot", "--ru", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"]
    )
    out = _output(result)
    assert "ошибка:" in out and "--yes" in out


def test_service_logs_writes_local_file(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    out_dir = tmp_path / "dumpdir"
    result = runner.invoke(
        app,
        ["service", "logs", "--since", "6h", "--out", str(out_dir),
         "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"],
    )
    assert result.exit_code == 0, _output(result)
    files = list(out_dir.glob("logs-1.2.3.4-*.txt"))
    assert len(files) == 1
    assert "sample journal line" in files[0].read_text(encoding="utf-8")
    assert any(c.startswith("sudo -n journalctl -u xray -u xray-obs-snapshot") for c in FakeRemote.calls)
    assert not any("/tmp/xray-vpn-logs" in c for c in FakeRemote.calls)


def test_service_logs_rejects_bad_since(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    result = runner.invoke(
        app,
        ["service", "logs", "--since", "yesterday; rm -rf /",
         "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"],
    )
    assert result.exit_code == 2
    assert "invalid --since" in _output(result)
    assert not any("rm -rf" in c for c in FakeRemote.calls)


def test_service_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["service", "--help"])
    out = _output(result)
    assert "status" in out and "restart" in out and "logs" in out and "reboot" in out
    root = runner.invoke(app, ["--help"])
    assert "service" in _output(root)


def test_repl_help_mentions_service() -> None:
    assert "service status|restart|logs|reboot" in help_text()


def test_service_restart_output(monkeypatch, tmp_path) -> None:
    _stub_transport(monkeypatch, tmp_path)
    key = _key(tmp_path)
    result = runner.invoke(
        app, ["service", "restart", "-H", "1.2.3.4", "--pkey", str(key), "--no-interactive"]
    )
    assert result.exit_code == 0, _output(result)
    assert "[done] xray restarted (active)" in _output(result)
    assert "sudo -n systemctl restart xray" in FakeRemote.calls
