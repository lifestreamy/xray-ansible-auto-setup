"""xrayvpn CLI entry point (Typer app).

Full flag surface is added incrementally; `--version` works from the start.
"""

from __future__ import annotations

import typer

from xrayvpn import __version__

app = typer.Typer(
    name="xrayvpn",
    help="Provision Xray VLESS + REALITY VPN servers (local or remote execution).",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"xrayvpn {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """xrayvpn — one client, two execution modes (local / remote)."""