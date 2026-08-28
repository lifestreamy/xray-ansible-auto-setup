"""xrayvpn CLI (Typer).

`xrayvpn deploy` — one command, two execution modes (ADR-003):

- `--execution local`  — run the playbook against the current machine
  (Windows: via the WSL bridge);
- `--execution remote` — bootstrap and provision a remote VPS over SSH
  (wired in a later step; see cli/remote).

The flag surface covers the legacy shell clients' options plus the deploy
overrides (runtime, port, client count, WARP, rotation, firewall).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from xrayvpn import __version__
from xrayvpn.cli import prompts
from xrayvpn.core.config import find_repo_root, load_settings, merge_overrides
from xrayvpn.core.execution.base import DeployRequest
from xrayvpn.core.execution.local import DEFAULT_WSL_VENV, LocalExecutor
from xrayvpn.core.inventory import build_inventory, write_inventory

SUPPORTED_RUNTIMES = ("native", "docker", "podman")
EXECUTION_MODES = ("local", "remote")

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
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """xrayvpn — one client, two execution modes (local / remote)."""


def _resolve_execution(execution: str | None) -> str:
    if execution is None:
        selected = prompts.select(
            "Execution mode", list(EXECUTION_MODES), default="local"
        )
        execution = selected or "local"
    if execution not in EXECUTION_MODES:
        typer.echo(f"error: unknown execution mode: {execution}", err=True)
        raise typer.Exit(2)
    return execution


def _collect_overrides(args: dict) -> dict[str, object]:
    overrides: dict[str, object] = {}
    if args.get("runtime") is not None:
        overrides["xray_runtime"] = args["runtime"]
    if args.get("xray_port") is not None:
        overrides["xray_port"] = args["xray_port"]
    if args.get("num_clients") is not None:
        overrides["num_clients"] = args["num_clients"]
    if args.get("camouflage_domain") is not None:
        overrides["reality_camouflage_domain"] = args["camouflage_domain"]
    if args.get("warp") is not None:
        overrides["warp_enabled"] = args["warp"]
    if args.get("rotate") is not None:
        overrides["xray_reality_rotate"] = args["rotate"]
    if args.get("manage_firewall") is not None:
        overrides["xray_manage_firewall"] = args["manage_firewall"]
    return overrides


@app.command()
def deploy(
    execution: Annotated[
        str | None,
        typer.Option(
            "--execution",
            help=f"Execution mode: {'|'.join(EXECUTION_MODES)} (default: local)",
        ),
    ] = None,
    runtime: Annotated[
        str | None,
        typer.Option(
            "--runtime",
            help=f"xray_runtime override ({', '.join(SUPPORTED_RUNTIMES)})",
        ),
    ] = None,
    xray_port: Annotated[
        int | None,
        typer.Option("--xray-port", help="VLESS inbound TCP port override"),
    ] = None,
    num_clients: Annotated[
        int | None,
        typer.Option("--num-clients", help="Number of client configs to generate"),
    ] = None,
    camouflage_domain: Annotated[
        str | None,
        typer.Option(
            "--camouflage-domain", help="REALITY camouflage/SNI domain override"
        ),
    ] = None,
    warp: Annotated[
        bool | None,
        typer.Option("--warp/--no-warp", help="Enable/disable Cloudflare WARP outbound"),
    ] = None,
    rotate: Annotated[
        bool | None,
        typer.Option(
            "--rotate/--no-rotate",
            help="Force REALITY key + UUID regeneration / keep existing state",
        ),
    ] = None,
    manage_firewall: Annotated[
        bool | None,
        typer.Option(
            "--manage-firewall/--no-firewall",
            help="Enable/disable ufw management (disable on WSL test hosts)",
        ),
    ] = None,
    inventory: Annotated[
        Path | None,
        typer.Option(
            "--inventory",
            help="Use an existing inventory file instead of the generated one",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Pass --check to ansible-playbook; no changes"),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Ansible -vvv + xray_debug=true"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Ansible -vvvv + xray_debug=true"),
    ] = False,
    wsl_distro: Annotated[
        str | None,
        typer.Option("--wsl-distro", help="WSL distro for local mode (default distro)"),
    ] = None,
    wsl_venv: Annotated[
        str,
        typer.Option(
            "--wsl-venv",
            help="WSL venv holding ansible-playbook (local mode)",
        ),
    ] = DEFAULT_WSL_VENV,
) -> None:
    """Run the deploy playbook. Local mode runs it on the current machine."""
    if debug and verbose:
        typer.echo("error: --debug and --verbose are mutually exclusive", err=True)
        raise typer.Exit(2)
    if runtime is not None and runtime not in SUPPORTED_RUNTIMES:
        typer.echo(
            f"error: --runtime must be one of {', '.join(SUPPORTED_RUNTIMES)}",
            err=True,
        )
        raise typer.Exit(2)

    mode = _resolve_execution(execution)
    if mode == "remote":
        typer.echo("error: remote execution is not available yet", err=True)
        raise typer.Exit(2)

    repo_root = find_repo_root()
    settings = load_settings(repo_root)
    overrides = _collect_overrides(locals())
    merged = merge_overrides(settings, overrides)
    verbosity = 4 if verbose else (3 if debug else 0)

    request = DeployRequest(
        repo_root=repo_root,
        overrides=overrides,
        dry_run=dry_run,
        verbosity=verbosity,
        debug=debug,
        inventory_path=inventory,
    )
    if inventory is None:
        content = build_inventory(merged, connection="local")
        write_inventory(repo_root, content)

    executor = LocalExecutor(wsl_distro=wsl_distro or None, wsl_venv=wsl_venv)
    rc = executor.deploy(request)
    if rc != 0:
        raise typer.Exit(rc)
    if not dry_run:
        executor.fetch_configs(request)
    typer.echo(f"[done] configs written to {request.resolved_clients_dir()}")


if __name__ == "__main__":
    sys.exit(app())