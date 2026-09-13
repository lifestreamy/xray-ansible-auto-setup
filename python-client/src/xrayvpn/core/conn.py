"""Resolve an SSH connection from flags or the personal inventory (service wave).

Mirrors the semantics already validated in the deploy flow, as one reusable
helper. Deploy keeps its inline blocks until the core-refactoring card
migrates them here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from xrayvpn.core.inventory import (
    parse_user_inventory,
    user_inventory_hosts,
    validate_connection,
)


class ConnResolveError(RuntimeError):
    """Operator-facing connection problem; the CLI prints it as `error: …`."""


@dataclass(frozen=True)
class ResolvedConnection:
    host: str
    user: str = "root"
    port: int = 22
    pkey: str | None = None
    password: str | None = None


def resolve_connection(
    *,
    workspace: Path,
    example_dir: Path,
    host: str | None = None,
    user: str = "root",
    port: int = 22,
    pkey: Path | str | None = None,
    password: str | None = None,
    use_inventory: bool = False,
    no_interactive: bool = False,
    ask_host: Callable[[str], str | None] | None = None,
    ask_password: Callable[[str], str] | None = None,
) -> ResolvedConnection:
    """flags+inventory -> one usable SSH connection (single-host contract).

    `ask_host`/`ask_password` are injected by the CLI (prompts/getpass); in
    non-interactive runs their absence is an error like in the deploy guards.
    """
    if use_inventory:
        try:
            hosts = user_inventory_hosts(workspace)
        except RuntimeError:
            hosts = []  # missing file: parse_user_inventory below raises with the template hint
        if len(hosts) > 1:
            raise ConnResolveError(
                "inventory.yml defines multiple hosts: "
                f"{', '.join(sorted(hosts))}; keep a single host in the inventory "
                "or pass connection flags instead of --use-inventory"
            )
        try:
            connection, _ = parse_user_inventory(workspace, example_dir=example_dir)
        except (RuntimeError, TypeError) as exc:
            raise ConnResolveError(str(exc)) from exc
        problems = validate_connection(connection)
        if problems:
            raise ConnResolveError("; ".join(problems))
        host = connection.get("ansible_host") or None
        user = connection.get("ansible_user") or "root"
        port = int(connection.get("ansible_port") or "22")
        pkey = connection.get("ansible_ssh_private_key_file") or None
        password = connection.get("ansible_ssh_pass") or None
    else:
        host = (host or "").strip() or None

    if not host:
        if no_interactive or ask_host is None:
            raise ConnResolveError(
                "VPS host required: pass --host or run interactively (or --use-inventory)"
            )
        host = (ask_host("VPS host (IP or hostname)") or "").strip()
        if not host:
            raise ConnResolveError("--host is required")

    if pkey and password:
        raise ConnResolveError("both a private key and a password are configured; use one")

    if pkey:
        key_path = Path(str(pkey)).expanduser()
        if not key_path.is_file():
            raise ConnResolveError(f"private key not found: {key_path}")
        pkey = str(key_path)
    elif not password:
        if no_interactive or ask_password is None:
            raise ConnResolveError(
                "SSH auth required: --pkey, --pass or inventory auth "
                "(no password prompt in non-interactive mode)"
            )
        password = ask_password("SSH password: ")

    return ResolvedConnection(host=host, user=user, port=port, pkey=pkey, password=password)
