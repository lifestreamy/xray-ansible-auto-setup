"""Semantic color tokens for CLI output.

ANSI color names only (no hex — the Windows console legacy path); the hex
palette belongs to the TUI stage. Five roles cover the whole CLI surface:
ok / error / warn / muted / accent. Styling never decides semantics: callers
pick the role, `typer.echo` strips the codes on non-tty output, and NO_COLOR
disables them at the source.
"""

from __future__ import annotations

import os

import typer

TOKENS: dict[str, str] = {
    "ok": "green",
    "error": "red",
    "warn": "yellow",
    "muted": "dim",
    "accent": "bright_green",
}


def _styled(text: str, token: str) -> str:
    if os.environ.get("NO_COLOR"):
        return text
    color = TOKENS[token]
    if color == "dim":
        return typer.style(text, dim=True)
    return typer.style(text, fg=color)


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
