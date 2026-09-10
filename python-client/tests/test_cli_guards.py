"""CLI guards: flag/mode validation and the deploy-plan confirmation policy."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from typer.testing import CliRunner

import xrayvpn.cli.main as main_mod
from xrayvpn.cli.main import app

runner = CliRunner()


def _output(result) -> str:
    text = result.output or ""
    stderr = getattr(result, "stderr", "") or ""
    return text + stderr


class RecordingExecutor:
    """Stands in for LocalExecutor; records calls, returns a fixed rc."""

    instances: ClassVar[list[RecordingExecutor]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.deployed_with: tuple | None = None
        self.fetched = False
        RecordingExecutor.instances.append(self)

    def venv_binary(self) -> str:
        return "ansible-playbook"

    def preflight(self, *, password_auth: bool) -> None:
        self.password_auth = password_auth

    def deploy(self, request: object, inventory: Path) -> int:
        self.deployed_with = (request, inventory)
        return 0

    def fetch_configs(self, request: object, inventory: Path) -> None:
        self.fetched = True


def _stub_local_mode(
    monkeypatch,
    tmp_path: Path,
) -> dict[str, object]:
    """Isolate _run_local: fake repo root, recording executor, fake inventory."""
    RecordingExecutor.instances = []
    written: dict[str, object] = {}
    fake_inv = tmp_path / "inv.yml"

    def fake_write_inventory(repo_root: Path, content: str) -> Path:
        fake_inv.write_text(content, encoding="utf-8")
        written["content"] = content
        return fake_inv

    monkeypatch.setattr(main_mod, "find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(main_mod, "load_settings", lambda root: {})
    monkeypatch.setattr(main_mod, "write_inventory", fake_write_inventory)
    monkeypatch.setattr(main_mod, "LocalExecutor", RecordingExecutor)
    return written


def test_inventory_requires_local_mode() -> None:
    result = runner.invoke(app, ["deploy", "--inventory", "x.yml"])
    assert result.exit_code == 2
    assert "--execution local" in _output(result)


def test_unknown_execution_mode_rejected() -> None:
    result = runner.invoke(app, ["deploy", "--execution", "cloud"])
    assert result.exit_code == 2
    assert "unknown execution mode" in _output(result)


def test_default_execution_is_remote_noninteractive() -> None:
    """No flag + non-interactive stdin must resolve remote (never silent local);
    dry-run shows the remote preview and never connects."""
    result = runner.invoke(app, ["deploy", "--dry-run"])
    assert result.exit_code == 0
    assert "[preview] remote deploy" in _output(result)


def test_confirmation_blocks_run_without_terminal(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_mod.prompts, "is_interactive", lambda: False)
    _stub_local_mode(monkeypatch, tmp_path)
    key = tmp_path / "id_ed25519"
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        ["deploy", "--execution", "local", "-H", "203.0.113.7", "--pkey", str(key)],
    )
    assert result.exit_code == 2
    assert "confirmation needs a terminal" in _output(result)
    assert RecordingExecutor.instances == []


def test_declined_plan_aborts_before_any_work(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_mod.prompts, "is_interactive", lambda: True)
    monkeypatch.setattr(main_mod.prompts, "confirm", lambda *a, **k: False)
    _stub_local_mode(monkeypatch, tmp_path)
    key = tmp_path / "id_ed25519"
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        ["deploy", "--execution", "local", "-H", "203.0.113.7", "--pkey", str(key)],
    )
    assert result.exit_code == 0
    out = _output(result)
    assert "[abort]" in out
    assert "deploy plan:" in out
    assert "auth: SSH key" in out
    assert RecordingExecutor.instances == []


def test_no_interactive_runs_and_writes_ssh_inventory(monkeypatch, tmp_path) -> None:
    written = _stub_local_mode(monkeypatch, tmp_path)
    key = tmp_path / "id_ed25519"
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "deploy",
            "--execution",
            "local",
            "-H",
            "203.0.113.7",
            "-u",
            "root",
            "--pkey",
            str(key),
            "--no-interactive",
        ],
    )
    assert result.exit_code == 0
    executor = RecordingExecutor.instances[-1]
    assert executor.deployed_with is not None
    content = str(written["content"])
    assert "ansible_connection: ssh" in content
    assert "ansible_host: 203.0.113.7" in content
    assert "ansible_ssh_private_key_file" in content
    assert executor.fetched
    assert "[done] configs written to" in _output(result)


def test_rotate_warning_in_plan(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_mod.prompts, "is_interactive", lambda: True)
    monkeypatch.setattr(main_mod.prompts, "confirm", lambda *a, **k: False)
    _stub_local_mode(monkeypatch, tmp_path)
    key = tmp_path / "id_ed25519"
    key.write_text("x", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "deploy",
            "--execution",
            "local",
            "-H",
            "203.0.113.7",
            "--pkey",
            str(key),
            "--rotate",
        ],
    )
    out = _output(result)
    assert "REALITY keys and client UUIDs will be regenerated" in out


def test_mutual_exclusions_keep_working() -> None:
    result = runner.invoke(app, ["deploy", "--full-cleanup", "--no-cleanup"])
    assert result.exit_code == 2
    assert "mutually exclusive" in _output(result)
    result = runner.invoke(app, ["deploy", "--pkey", "k", "--pass", "p"])
    assert result.exit_code == 2
    assert "--pkey and --pass" in _output(result)
    result = runner.invoke(app, ["deploy", "--runtime", "podman"])
    assert result.exit_code == 2
    assert "--runtime must be one of" in _output(result)
