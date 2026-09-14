"""Theme tokens: NO_COLOR, non-tty stripping, and the color-literal guard."""

from __future__ import annotations

import re
from pathlib import Path

import typer
from typer.testing import CliRunner

import xrayvpn
from xrayvpn.cli import theme

PACKAGE = Path(xrayvpn.__file__).resolve().parent
HELPERS = (theme.ok, theme.err, theme.warn, theme.muted, theme.accent)


def test_tokens_are_hex_palette() -> None:
    assert theme.TOKENS == {
        "ok": "#1DB954",
        "error": "#F85149",
        "warn": "#D29922",
        "muted": "#A8B2BE",
        "accent": "#00D587",
    }


def test_tokens_match_assets_color_tokens_json() -> None:
    import json

    tokens_file = PACKAGE.parents[2] / "assets" / "color-tokens.json"
    mirror = json.loads(tokens_file.read_text(encoding="utf-8"))
    assert mirror == theme.TOKENS


def test_visible_len_ignores_ansi(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    styled = theme.accent("abcd")
    assert styled != "abcd"
    assert theme.visible_len(styled) == 4
    assert theme.plain(styled) == "abcd"


def test_helpers_emit_ansi_by_default(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    for helper in HELPERS:
        assert "\x1b[" in helper("x")


def test_no_color_disables_codes(monkeypatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    for helper in HELPERS:
        assert helper("x") == "x"


def test_echo_strips_ansi_on_non_tty(monkeypatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    probe_app = typer.Typer()

    @probe_app.command()
    def probe() -> None:
        typer.echo(theme.ok("green text"))
        typer.echo(theme.err("red text"), err=True)

    result = CliRunner().invoke(probe_app, [])
    assert "green text" in result.output
    assert "\x1b[" not in result.output


def test_color_literals_live_only_in_theme() -> None:
    pattern = re.compile(r"typer\.style|click\.style|\\x1b\[|\bfg=")
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name == "theme.py" or path.parent.name in ("payload", "build"):
            continue
        if pattern.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert not offenders
