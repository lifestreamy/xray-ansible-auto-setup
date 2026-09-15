"""apply_palette(): rich help panels re-style onto theme.TOKENS (typer-pin guard)."""

from __future__ import annotations

from typer import rich_utils

from xrayvpn.cli import l10n_typer, theme


def test_apply_palette_sets_all_overrides() -> None:
    l10n_typer.apply_palette()
    for name, value in l10n_typer.PALETTE_OVERRIDES.items():
        assert getattr(rich_utils, name) == value


def test_overrides_derive_from_theme_tokens_single_source() -> None:
    assert l10n_typer.PALETTE_OVERRIDES["STYLE_OPTION"] == (
        f"bold {theme.TOKENS['accent']}"
    )
    assert l10n_typer.PALETTE_OVERRIDES["STYLE_NEGATIVE_SWITCH"] == (
        f"bold {theme.TOKENS['ok']}"
    )
    assert l10n_typer.PALETTE_OVERRIDES["STYLE_TYPES"] == theme.TOKENS["muted"]
    assert l10n_typer.PALETTE_OVERRIDES["STYLE_ERRORS_PANEL_BORDER"] == (
        theme.TOKENS["error"]
    )


def test_palette_is_idempotent_and_survives_ru_revert() -> None:
    l10n_typer.apply_palette()
    snapshot = {n: getattr(rich_utils, n) for n in l10n_typer.PALETTE_OVERRIDES}
    l10n_typer.apply_ru()
    l10n_typer.revert_ru()
    l10n_typer.apply_palette()
    assert {n: getattr(rich_utils, n) for n in l10n_typer.PALETTE_OVERRIDES} == snapshot
