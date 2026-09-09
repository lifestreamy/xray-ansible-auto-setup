"""Minimal RU/EN switch for user-facing CLI strings (`--ru`).

Help texts stay English (Typer builds them at import time); prompts,
runtime messages and errors are translated via `t(en, ru)`.
"""

from __future__ import annotations

_STATE = {"ru": False}


def set_ru(enabled: bool) -> None:
    _STATE["ru"] = bool(enabled)


def is_ru() -> bool:
    return _STATE["ru"]


def t(en: str, ru: str) -> str:
    """Return the RU or EN variant of a user-facing string."""
    return ru if _STATE["ru"] else en
