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
