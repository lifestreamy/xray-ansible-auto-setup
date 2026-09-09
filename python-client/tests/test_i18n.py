"""i18n: the --ru flag switches user-facing prompts/messages/errors to Russian."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from xrayvpn import i18n
from xrayvpn.cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_i18n():
    yield
    i18n.set_ru(False)


def _output(result) -> str:
    text = result.output or ""
    stderr = getattr(result, "stderr", "") or ""
    return text + stderr


def test_t_switch() -> None:
    assert i18n.t("yes", "да") == "yes"
    i18n.set_ru(True)
    assert i18n.t("yes", "да") == "да"
    assert i18n.is_ru()


def test_ru_flag_on_command_translates_guard_error() -> None:
    result = runner.invoke(app, ["deploy", "--ru", "--debug", "--verbose"])
    assert result.exit_code == 2
    assert "взаимоисключающие" in _output(result)


def test_ru_flag_before_command_translates_guard_error() -> None:
    result = runner.invoke(app, ["--ru", "deploy", "--debug", "--verbose"])
    assert result.exit_code == 2
    assert "взаимоисключающие" in _output(result)


def test_default_output_stays_english() -> None:
    result = runner.invoke(app, ["deploy", "--debug", "--verbose"])
    assert result.exit_code == 2
    assert "mutually exclusive" in _output(result)


def test_ru_inventory_guard_translation() -> None:
    result = runner.invoke(app, ["deploy", "--ru", "--execution", "local", "--use-inventory"])
    assert result.exit_code == 2
    assert "применим только к --execution remote" in _output(result)
