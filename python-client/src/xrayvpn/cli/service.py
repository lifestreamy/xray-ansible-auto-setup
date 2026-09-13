"""`xrayvpn service` — whitelisted recovery actions over the existing SSH transport."""

from __future__ import annotations

import getpass
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from xrayvpn import i18n
from xrayvpn.cli import prompts, repl
from xrayvpn.core.config import find_repo_root, load_settings, merge_overrides
from xrayvpn.core.conn import ConnResolveError, ResolvedConnection, resolve_connection
from xrayvpn.core.inventory import parse_user_inventory
from xrayvpn.core.runtime_paths import RunRoots, resolve_roots
from xrayvpn.core.service_actions import (
    logs_journal_command,
    reboot_command,
    restart_commands,
    status_commands,
)
from xrayvpn.core.transport.remote import FabricRemote, SshConnectError

HOST_OPT = Annotated[
    str | None,
    typer.Option(
        "--host", "-H",
        help=i18n.t("SVC_HOST_OPT"),
    ),
]
USER_OPT = Annotated[
    str,
    typer.Option("--user", "-u", help=i18n.t("COMMON_USER")),
]
PORT_OPT = Annotated[
    int,
    typer.Option("--port", "-p", help=i18n.t("COMMON_PORT")),
]
PKEY_OPT = Annotated[
    Path | None,
    typer.Option(
        "--pkey", help=i18n.t("COMMON_PKEY")
    ),
]
PASS_OPT = Annotated[
    str | None,
    typer.Option(
        "--pass",
        help=i18n.t("COMMON_PASS"),
    ),
]
INVENTORY_OPT = Annotated[
    bool,
    typer.Option(
        "--use-inventory",
        help=i18n.t("SVC_INVENTORY_OPT"),
    ),
]
RU_OPT = Annotated[
    bool,
    typer.Option(
        "--ru",
        help=i18n.t("SVC_RU_OPT"),
    ),
]
NO_INTERACTIVE_OPT = Annotated[
    bool,
    typer.Option(
        "--no-interactive",
        help=i18n.t("SVC_NOINT_OPT"),
    ),
]

SINCE_OPT = Annotated[
    str,
    typer.Option(
        "--since",
        help=i18n.t("SVC_SINCE_OPT"),
    ),
]
OUT_OPT = Annotated[
    Path | None,
    typer.Option(
        "--out",
        help=i18n.t("SVC_OUT_OPT"),
    ),
]
YES_OPT = Annotated[
    bool,
    typer.Option(
        "--yes",
        help=i18n.t("SVC_YES_OPT"),
    ),
]

_SINCE_RE = re.compile(r"^-?(\d+)(m|h|d)$")

service_app = typer.Typer(
    help=i18n.t("SVC_HELP"),
    no_args_is_help=True,
)


def _fail(message: str) -> NoReturn:
    typer.echo(i18n.t("COMMON_ERR", err=message), err=True)
    raise typer.Exit(2)


def _normalize_since(value: str) -> str:
    match = _SINCE_RE.match(value.strip())
    if not match:
        _fail(i18n.t("SVC_SINCE_INVALID", value=value))
    return f"{match.group(1)}{match.group(2)}"


def _roots() -> RunRoots:
    return resolve_roots(find_repo=find_repo_root)


def _resolve_conn(
    host: str | None,
    user: str,
    port: int,
    pkey: Path | None,
    password: str | None,
    use_inventory: bool,
    no_interactive: bool,
    roots: RunRoots,
) -> ResolvedConnection:
    interactive = prompts.is_interactive() and not no_interactive
    try:
        return resolve_connection(
            workspace=roots.workspace,
            example_dir=roots.payload,
            host=host,
            user=user,
            port=port,
            pkey=pkey,
            password=password,
            use_inventory=use_inventory,
            no_interactive=no_interactive,
            ask_host=(lambda q: prompts.text(i18n.t("COMMON_HOST_PROMPT"))) if interactive else None,
            ask_password=(lambda _q: getpass.getpass(i18n.t("COMMON_SSH_PASS_PROMPT"))) if interactive else None,
        )
    except ConnResolveError as exc:
        _fail(str(exc))


@contextmanager
def _open(conn: ResolvedConnection) -> Iterator[FabricRemote]:
    try:
        with FabricRemote(
            conn.host,
            user=conn.user,
            port=conn.port,
            key_filename=conn.pkey,
            password=conn.password,
        ) as remote:
            yield remote
    except SshConnectError as exc:
        _fail(str(exc))


def _settings_ports(roots: RunRoots, use_inventory: bool) -> tuple[int, int]:
    try:
        settings = load_settings(roots.repo)
    except (RuntimeError, OSError):
        settings = {}
    if use_inventory:
        # deploy-identical override chain: inventory user_vars win over settings.yml
        try:
            _, user_vars = parse_user_inventory(roots.workspace, example_dir=roots.payload)
            settings = merge_overrides(settings, user_vars)
        except (RuntimeError, TypeError):
            pass
    return (
        int(settings.get("xray_port", 443)),
        int(settings.get("xray_watchdog_probe_port", 10820)),
    )


def _apply_ru(ru: bool) -> None:
    if ru:
        repl.set_session_lang("ru")


@service_app.command("status")
def service_status(
    host: HOST_OPT = None,
    user: USER_OPT = "root",
    port: PORT_OPT = 22,
    pkey: PKEY_OPT = None,
    password: PASS_OPT = None,
    use_inventory: INVENTORY_OPT = False,
    ru: RU_OPT = False,
    no_interactive: NO_INTERACTIVE_OPT = False,
) -> None:
    """Show service state, journal tail, listeners and memory."""
    _apply_ru(ru)
    roots = _roots()
    conn = _resolve_conn(host, user, port, pkey, password, use_inventory, no_interactive, roots)
    xray_port, probe_port = _settings_ports(roots, use_inventory)
    with _open(conn) as remote:
        results = [remote.run(cmd, warn=True) for cmd in status_commands(xray_port, probe_port)]
    active = results[0].stdout.strip() or "?"
    facts = dict(
        line.split("=", 1) for line in results[1].stdout.splitlines() if "=" in line
    )
    storm = results[2].stdout.strip() or "?"
    typer.echo(i18n.t(
        "SVC_STATUS_TITLE", host=conn.host, port=conn.port, active=active
    ))
    typer.echo(i18n.t(
        "SVC_STATUS_FACTS",
        n=facts.get("NRestarts", "?"),
        since=facts.get("ActiveEnterTimestamp", "?"),
        sub=facts.get("SubState", "?"),
    ))
    typer.echo(i18n.t("SVC_STATUS_STORM", count=storm))
    typer.echo(i18n.t("SVC_JOURNAL_TAIL"))
    for line in results[3].stdout.splitlines()[-30:]:
        typer.echo(f"  {line}")
    typer.echo(i18n.t("SVC_LISTENERS"))
    for line in results[4].stdout.splitlines():
        typer.echo(f"  {line}")
    typer.echo(i18n.t("SVC_MEMORY"))
    for line in results[5].stdout.splitlines()[:3]:
        typer.echo(f"  {line}")
    raise typer.Exit(0 if active == "active" else 1)


@service_app.command("restart")
def service_restart(
    host: HOST_OPT = None,
    user: USER_OPT = "root",
    port: PORT_OPT = 22,
    pkey: PKEY_OPT = None,
    password: PASS_OPT = None,
    use_inventory: INVENTORY_OPT = False,
    ru: RU_OPT = False,
    no_interactive: NO_INTERACTIVE_OPT = False,
) -> None:
    """Point-restart xray.service (WARP lives inside it; the host is untouched)."""
    _apply_ru(ru)
    roots = _roots()
    conn = _resolve_conn(host, user, port, pkey, password, use_inventory, no_interactive, roots)
    with _open(conn) as remote:
        for cmd in restart_commands()[:2]:
            result = remote.run(cmd, warn=True)
            if result.failed:
                _fail(f"{cmd} → rc={result.return_code} {result.stderr.strip()[:200]}")
        after = remote.run(restart_commands()[2], warn=True).stdout.strip()
    typer.echo(i18n.t("SVC_RESTARTED", state=after))
    raise typer.Exit(0 if after == "active" else 1)


@service_app.command("logs")
def service_logs(
    host: HOST_OPT = None,
    user: USER_OPT = "root",
    port: PORT_OPT = 22,
    pkey: PKEY_OPT = None,
    password: PASS_OPT = None,
    use_inventory: INVENTORY_OPT = False,
    ru: RU_OPT = False,
    no_interactive: NO_INTERACTIVE_OPT = False,
    since: SINCE_OPT = "24h",
    out: OUT_OPT = None,
) -> None:
    """Dump the server journal (xray + obs + watchdog) to a local file."""
    _apply_ru(ru)
    since_norm = _normalize_since(since)
    roots = _roots()
    conn = _resolve_conn(host, user, port, pkey, password, use_inventory, no_interactive, roots)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if out is not None and (out.suffix == ".txt" or (out.exists() and out.is_file())):
        local = out.expanduser().resolve()
    else:
        target_dir = (out.expanduser().resolve() if out is not None else roots.workspace / "logs")
        target_dir.mkdir(parents=True, exist_ok=True)
        local = target_dir / f"logs-{conn.host}-{stamp}.txt"
    with _open(conn) as remote:
        dump = remote.run(logs_journal_command(since_norm), warn=True)
    if dump.failed:
        _fail(f"log read failed (rc={dump.return_code}) {dump.stderr.strip()[:200]}")
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(dump.stdout, encoding="utf-8")
    typer.echo(i18n.t("SVC_LOGS_SAVED", since=since_norm, path=local))


@service_app.command("reboot")
def service_reboot(
    host: HOST_OPT = None,
    user: USER_OPT = "root",
    port: PORT_OPT = 22,
    pkey: PKEY_OPT = None,
    password: PASS_OPT = None,
    use_inventory: INVENTORY_OPT = False,
    ru: RU_OPT = False,
    no_interactive: NO_INTERACTIVE_OPT = False,
    yes: YES_OPT = False,
) -> None:
    """Reboot the HOST — the last resort; explicit --yes is mandatory."""
    _apply_ru(ru)
    if not yes:
        typer.echo(i18n.t("SVC_REBOOT_NEED_YES"), err=True)
        raise typer.Exit(2)
    roots = _roots()
    conn = _resolve_conn(host, user, port, pkey, password, use_inventory, no_interactive, roots)
    with _open(conn) as remote:
        result = remote.run(reboot_command(), warn=True)
    if result.failed:
        _fail(f"reboot failed (rc={result.return_code}) {result.stderr.strip()[:200]}")
    typer.echo(i18n.t("SVC_REBOOTING", host=conn.host))
