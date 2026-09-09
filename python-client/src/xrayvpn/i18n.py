"""RU/EN switch for user-facing CLI strings (`--ru`, `XRAYVPN_LANG`).

`preinit()` runs before the Typer app is built, so `--ru` in any argv
position or `XRAYVPN_LANG=ru` also translates `--help`: Typer bakes help
texts at import time. Two-letter language codes keep the door open for
more languages; the internal state is currently a RU boolean and `t(en, ru)`
is the translation primitive.
"""

from __future__ import annotations

import os
import sys

LANG_ENV = "XRAYVPN_LANG"

_STATE = {"ru": False}


def set_ru(enabled: bool) -> None:
    _STATE["ru"] = bool(enabled)


def is_ru() -> bool:
    return _STATE["ru"]


def t(en: str, ru: str) -> str:
    """Return the RU or EN variant of a user-facing string."""
    return ru if _STATE["ru"] else en


def set_lang(lang: str) -> None:
    normalized = lang.strip().lower()
    if normalized == "ru":
        set_ru(True)
    elif normalized == "en":
        set_ru(False)
    else:
        set_ru(False)
        print(
            f"warning: unknown {LANG_ENV} value {lang!r}; falling back to English",
            file=sys.stderr,
        )


def preinit(argv: list[str] | None = None) -> None:
    """Detect the language before the Typer app is built: env first, `--ru` wins."""
    args = sys.argv[1:] if argv is None else argv
    env_lang = os.environ.get(LANG_ENV, "").strip()
    if env_lang:
        set_lang(env_lang)
    if "--ru" in args:
        set_ru(True)
