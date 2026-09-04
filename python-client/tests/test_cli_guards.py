"""CLI guards: inventory flags rejected in the wrong execution mode."""

from __future__ import annotations

from typer.testing import CliRunner

from xrayvpn.cli.main import app

runner = CliRunner()


def _output(result) -> str:
    text = result.output or ""
    stderr = getattr(result, "stderr", "") or ""
    return text + stderr


def test_use_inventory_rejected_in_local_mode() -> None:
    result = runner.invoke(app, ["deploy", "--execution", "local", "--use-inventory"])
    assert result.exit_code == 2
    assert "--execution remote" in _output(result)


def test_inventory_rejected_in_remote_mode() -> None:
    result = runner.invoke(app, ["deploy", "--execution", "remote", "--inventory", "x.yml"])
    assert result.exit_code == 2
    assert "--execution local" in _output(result)


def test_local_missing_venv_reported_as_guard_error(
    tmp_path, monkeypatch
) -> None:
    """RuntimeError from the executor surfaces as `error:` + exit 2, not a traceback."""

    class ExplodingExecutor:
        def __init__(self, **kwargs: object) -> None:
            pass

        def deploy(self, request: object) -> int:
            raise RuntimeError("ansible-playbook not found (scripts/dev/setup_test_env.py)")

    inventory = tmp_path / "inv.yml"
    inventory.write_text("all:\n  hosts: {}\n", encoding="utf-8")
    monkeypatch.setattr("xrayvpn.cli.main.find_repo_root", lambda: tmp_path)
    monkeypatch.setattr("xrayvpn.cli.main.load_settings", lambda root: {})
    monkeypatch.setattr("xrayvpn.cli.main.LocalExecutor", ExplodingExecutor)
    result = runner.invoke(
        app, ["deploy", "--execution", "local", "--inventory", str(inventory)]
    )
    assert result.exit_code == 2
    out = _output(result)
    assert "error:" in out
    assert "setup_test_env" in out
    assert "Traceback" not in out
