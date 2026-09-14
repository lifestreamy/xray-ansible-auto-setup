"""Semantic color tokens for CLI output.

Truecolor hex palette (Windows 10+/modern terminals; legacy conhost degrades).
Five roles cover the whole CLI surface: ok / error / warn / muted / accent.
Styling never decides semantics: callers pick the role, `typer.echo` strips
the codes on non-tty output, and NO_COLOR disables them at the source. The
design-time mirror of this palette lives in assets/color-tokens.json.
"""

from __future__ import annotations

import os
import re

import typer

TOKENS: dict[str, str] = {
    "ok": "#1DB954",
    "error": "#F85149",
    "warn": "#D29922",
    "muted": "#A8B2BE",
    "accent": "#00D587",
}

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


def visible_len(text: str) -> int:
    return len(plain(text))


def _rgb(token: str) -> tuple[int, int, int]:
    value = TOKENS[token].lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _styled(text: str, token: str) -> str:
    if os.environ.get("NO_COLOR"):
        return text
    return typer.style(text, fg=_rgb(token))


def ok(text: str) -> str:
    return _styled(text, "ok")


def err(text: str) -> str:
    return _styled(text, "error")


def warn(text: str) -> str:
    return _styled(text, "warn")


def muted(text: str) -> str:
    return _styled(text, "muted")


def accent(text: str) -> str:
    return _styled(text, "accent")
