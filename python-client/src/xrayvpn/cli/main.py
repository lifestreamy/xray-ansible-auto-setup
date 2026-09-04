"""xrayvpn CLI (Typer).

`xrayvpn deploy` — one command, two execution modes (ADR-003):

- `--execution local`  — run the playbook against the current machine
  (Windows: via the WSL bridge);
- `--execution remote` — bootstrap and provision a remote VPS over SSH
  (Fabric transport; tarball upload; no GitHub dependency).

The flag surface covers the legacy shell clients' options plus the deploy
overrides (runtime, port, client count, WARP, rotation, firewall).
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Annotated

import typer

from xrayvpn import __version__
from xrayvpn.cli import prompts
from xrayvpn.core.config import find_repo_root, load_settings, merge_overrides
from xrayvpn.core.execution.base import DeployRequest
from xrayvpn.core.execution.local import DEFAULT_WSL_VENV, LocalExecutor
from xrayvpn.core.execution.remote import (
    RemoteExecutor,
    bootstrap_commands,
    cleanup_commands,
    playbook_command,
)
from xrayvpn.core.inventory import (
    build_inventory,
    parse_user_inventory,
    validate_connection,
    write_inventory,
)
from xrayvpn.core.transport.remote import FabricRemote

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
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="VPS host/IP (remote mode; required)"),
    ] = None,
    user: Annotated[
        str,
        typer.Option("--user", "-u", help="SSH user (remote mode)"),
    ] = "root",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="SSH port (remote mode)"),
    ] = 22,
    pkey: Annotated[
        Path | None,
        typer.Option("--pkey", help="Path to an SSH private key (remote mode)"),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option("--pass", help="SSH password (remote mode; avoid, prefer --pkey)"),
    ] = None,
    use_inventory: Annotated[
        bool,
        typer.Option(
            "--use-inventory",
            help="Read connection params and vars from the personal inventory.yml",
        ),
    ] = False,
    clients_dir: Annotated[
        Path | None,
        typer.Option(
            "--clients-dir", help="Where generated client configs are saved"
        ),
    ] = None,
    full_cleanup: Annotated[
        bool,
        typer.Option(
            "--full-cleanup",
            help="Remote cleanup: also remove the server-side venv",
        ),
    ] = False,
    no_cleanup: Annotated[
        bool,
        typer.Option("--no-cleanup", help="Remote cleanup: keep the staging dir"),
    ] = False,
) -> None:
    """Run the deploy playbook. Local mode runs it on the current machine."""
    if debug and verbose:
        typer.echo("error: --debug and --verbose are mutually exclusive", err=True)
        raise typer.Exit(2)
    if full_cleanup and no_cleanup:
        typer.echo("error: --full-cleanup and --no-cleanup are mutually exclusive", err=True)
        raise typer.Exit(2)
    if runtime is not None and runtime not in SUPPORTED_RUNTIMES:
        typer.echo(
            f"error: --runtime must be one of {', '.join(SUPPORTED_RUNTIMES)}",
            err=True,
        )
        raise typer.Exit(2)
    if pkey is not None and password is not None:
        typer.echo("error: --pkey and --pass are mutually exclusive", err=True)
        raise typer.Exit(2)

    mode = _resolve_execution(execution)

    if use_inventory and mode == "local":
        typer.echo(
            "error: --use-inventory applies to --execution remote only; "
            "local mode generates its own inventory",
            err=True,
        )
        raise typer.Exit(2)
    if inventory is not None and mode == "remote":
        typer.echo(
            "error: --inventory applies to --execution local only; "
            "remote mode reads the personal inventory.yml via --use-inventory",
            err=True,
        )
        raise typer.Exit(2)

    repo_root = find_repo_root()
    settings = load_settings(repo_root)
    overrides = _collect_overrides(locals())
    merged = merge_overrides(settings, overrides)
    verbosity = 4 if verbose else (3 if debug else 0)

    if mode == "remote":
        _run_remote(
            repo_root,
            overrides=overrides,
            host=host,
            user=user,
            port=port,
            pkey=pkey,
            password=password,
            use_inventory=use_inventory,
            clients_dir=clients_dir,
            cleanup="full-cleanup" if full_cleanup else ("no-cleanup" if no_cleanup else "cleanup"),
            dry_run=dry_run,
            verbosity=verbosity,
            debug=debug,
        )
        return

    request = DeployRequest(
        repo_root=repo_root,
        overrides=overrides,
        clients_dir=clients_dir,
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


def _run_remote(
    repo_root: Path,
    *,
    overrides: dict[str, object],
    host: str | None,
    user: str,
    port: int,
    pkey: Path | None,
    password: str | None,
    use_inventory: bool,
    clients_dir: Path | None,
    cleanup: str,
    dry_run: bool,
    verbosity: int,
    debug: bool,
) -> None:
    """Remote-mode entry: auth resolution, optional preview, then the executor."""
    user_vars: dict[str, object] = {}
    connection: dict[str, str] = {}
    if use_inventory:
        if host is not None or pkey is not None or password is not None or user != "root" or port != 22:
            typer.echo(
                "warning: --use-inventory overrides connection/auth flags",
                err=True,
            )
        try:
            connection, user_vars = parse_user_inventory(repo_root)
        except (RuntimeError, TypeError) as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(2) from exc
        problems = validate_connection(connection)
        if problems:
            typer.echo(
                f"error: {repo_root / 'inventory.yml'} is not ready for remote deploy:",
                err=True,
            )
            for problem in problems:
                typer.echo(f"  - {problem}", err=True)
            typer.echo(
                "  fill the keys under all.hosts.<host> as in inventory.yml.example",
                err=True,
            )
            raise typer.Exit(2)
        if not (
            connection.get("ansible_ssh_private_key_file")
            or connection.get("ansible_ssh_pass")
        ):
            typer.echo(
                "note: no auth key in inventory.yml; the SSH password will be "
                "requested at run time (or set ansible_ssh_private_key_file)",
                err=True,
            )
        extra_vars = merge_overrides(user_vars, overrides)
        resolved_host = connection.get("ansible_host")
        resolved_user = connection.get("ansible_user", "root")
        resolved_port = int(connection.get("ansible_port", "22"))
        resolved_pkey = connection.get("ansible_ssh_private_key_file")
        resolved_password = connection.get("ansible_ssh_pass")
        flag_values = (host, pkey, password)
        if any(v is not None for v in flag_values):
            host = None
            pkey = None
            password = None
    else:
        extra_vars = dict(overrides)
        resolved_host = (host or "").strip() or None
        resolved_user = user
        resolved_port = port
        resolved_pkey = pkey
        resolved_password = password

    if dry_run:
        _preview_remote(repo_root, extra_vars, resolved_host, cleanup, verbosity, debug)
        return

    if not resolved_host:
        selected = prompts.text("VPS host (IP or hostname)")
        if not selected:
            typer.echo("error: --host is required in remote mode", err=True)
            raise typer.Exit(2)
        resolved_host = selected

    if resolved_pkey is not None and resolved_password is not None:
        typer.echo(
            "error: both a private key and a password are configured; use one",
            err=True,
        )
        raise typer.Exit(2)
    if resolved_pkey is not None:
        key_path = Path(resolved_pkey).expanduser()
        if not key_path.is_file():
            typer.echo(f"error: private key not found: {key_path}", err=True)
            raise typer.Exit(2)
    elif resolved_password is None:
        resolved_password = getpass.getpass("SSH password: ")

    request = DeployRequest(
        repo_root=repo_root,
        overrides=overrides,
        clients_dir=clients_dir,
        verbosity=verbosity,
        debug=debug,
    )
    with FabricRemote(
        resolved_host,
        user=resolved_user,
        port=resolved_port,
        key_filename=str(key_path) if resolved_pkey else None,
        password=resolved_password,
    ) as remote:
        executor = RemoteExecutor(remote, cleanup=cleanup)
        rc = executor.deploy(request, extra_vars=extra_vars)
    raise typer.Exit(rc)


def _preview_remote(
    repo_root: Path,
    extra_vars: dict[str, object],
    host: str | None,
    cleanup: str,
    verbosity: int,
    debug: bool,
) -> None:
    """Remote dry-run: show the plan without connecting anywhere."""
    typer.echo(f"[preview] remote deploy to {host or '<host>'}")
    for command in bootstrap_commands():
        typer.echo(f"[preview] $ {command}")
    typer.echo("[preview] upload tarball with (allowlist):")
    from xrayvpn.core import manifest

    for entry in manifest.allowlist_entries(repo_root):
        typer.echo(f"[preview]   {entry.name}")
    request = DeployRequest(repo_root=repo_root, overrides={}, verbosity=verbosity, debug=debug)
    typer.echo(f"[preview] $ {playbook_command(request, extra_vars)}")
    for command in cleanup_commands(cleanup):
        typer.echo(f"[preview] $ {command}")


if __name__ == "__main__":
    sys.exit(app())