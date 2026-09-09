"""xrayvpn CLI (Typer).

`xrayvpn deploy` — one command, two execution modes (ADR-003):

- `--execution local`  — run the playbook against the current machine
  (Windows: via the WSL bridge);
- `--execution remote` (default) — bootstrap and provision a remote VPS over
  SSH (Fabric transport; tarball upload; no GitHub dependency).

The flag surface covers the legacy shell clients' options plus the deploy
overrides (runtime, port, client count, WARP, rotation, ufw).
"""

from __future__ import annotations

import getpass
import sys
from pathlib import Path
from typing import Annotated

import typer

from xrayvpn import __version__, i18n
from xrayvpn.cli import l10n_typer, prompts
from xrayvpn.core.config import find_repo_root, load_settings, merge_overrides
from xrayvpn.core.execution.base import DeployRequest
from xrayvpn.core.execution.local import DEFAULT_WSL_VENV, LocalExecutor
from xrayvpn.core.execution.remote import (
    RemoteExecutor,
    bootstrap_commands,
    cleanup_commands,
    playbook_command,
    swap_guard_commands,
    swap_guard_needed,
    swap_status_commands,
)
from xrayvpn.core.inventory import (
    build_inventory,
    parse_user_inventory,
    validate_connection,
    write_inventory,
)
from xrayvpn.core.transport.remote import FabricRemote

SUPPORTED_RUNTIMES = ("native", "docker")
EXECUTION_MODES = ("local", "remote")

def _harden_stdio() -> None:
    """Redirected Windows streams default to the locale codec (cp1252) and
    crash on Cyrillic; UTF-8 keeps RU output intact in pipes and files."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        if stream.isatty():
            stream.reconfigure(errors="replace")
        else:
            stream.reconfigure(encoding="utf-8", errors="replace")


_harden_stdio()
i18n.preinit()
if i18n.is_ru():
    l10n_typer.apply_ru()

app = typer.Typer(
    name="xrayvpn",
    help=i18n.t(
        "Provision Xray VLESS + REALITY VPN servers (local or remote execution).",
        "Развёртывание VPN-серверов Xray VLESS + REALITY (локальное или удалённое исполнение).",
    ),
    no_args_is_help=True,
    add_completion=False,
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
            help=i18n.t("Show the version and exit.", "Показать версию и выйти."),
        ),
    ] = False,
    ru: Annotated[
        bool,
        typer.Option(
            "--ru",
            help=i18n.t(
                "Russian interface output (prompts, messages, errors, help)",
                "Русский вывод интерфейса (промпты, сообщения, ошибки, help)",
            ),
        ),
    ] = False,
) -> None:
    """xrayvpn — one client, two execution modes (local / remote)."""
    if ru:
        i18n.set_ru(True)


def _resolve_execution(execution: str | None) -> str:
    if execution is None:
        selected = prompts.select(
            i18n.t("Execution mode", "Режим исполнения"),
            list(EXECUTION_MODES),
            default="remote",
        )
        execution = selected or "remote"
    if execution not in EXECUTION_MODES:
        typer.echo(
            i18n.t(
                f"error: unknown execution mode: {execution}",
                f"ошибка: неизвестный режим исполнения: {execution}",
            ),
            err=True,
        )
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
    if args.get("manage_ufw") is not None:
        overrides["xray_manage_ufw"] = args["manage_ufw"]
    return overrides


@app.command(
    help=i18n.t(
        "Run the deploy playbook. Local mode runs it on the current machine.",
        "Запуск playbook развёртывания. Локальный режим выполняет его на этой машине.",
    )
)
def deploy(
    execution: Annotated[
        str | None,
        typer.Option(
            "--execution",
            help=i18n.t(
                f"Execution mode: {'|'.join(EXECUTION_MODES)} (default: remote)",
                f"Режим исполнения: {'|'.join(EXECUTION_MODES)} (по умолчанию remote)",
            ),
        ),
    ] = None,
    runtime: Annotated[
        str | None,
        typer.Option(
            "--runtime",
            help=i18n.t(
                f"xray_runtime override ({', '.join(SUPPORTED_RUNTIMES)})",
                f"Переопределение xray_runtime ({', '.join(SUPPORTED_RUNTIMES)})",
            ),
        ),
    ] = None,
    xray_port: Annotated[
        int | None,
        typer.Option(
            "--xray-port",
            help=i18n.t(
                "VLESS inbound TCP port override",
                "Переопределение TCP-порта входящего VLESS",
            ),
        ),
    ] = None,
    num_clients: Annotated[
        int | None,
        typer.Option(
            "--num-clients",
            help=i18n.t(
                "Number of client configs to generate",
                "Сколько клиентских конфигов генерировать",
            ),
        ),
    ] = None,
    camouflage_domain: Annotated[
        str | None,
        typer.Option(
            "--camouflage-domain",
            help=i18n.t(
                "REALITY camouflage/SNI domain override",
                "Переопределение домена маскировки REALITY (SNI)",
            ),
        ),
    ] = None,
    warp: Annotated[
        bool | None,
        typer.Option(
            "--warp/--no-warp",
            help=i18n.t(
                "Enable/disable Cloudflare WARP outbound",
                "Включить/выключить исходящий туннель Cloudflare WARP",
            ),
        ),
    ] = None,
    rotate: Annotated[
        bool | None,
        typer.Option(
            "--rotate/--no-rotate",
            help=i18n.t(
                "Force REALITY key + UUID regeneration / keep existing state",
                "Принудительно перегенерировать ключ REALITY и UUID / сохранить текущее состояние",
            ),
        ),
    ] = None,
    manage_ufw: Annotated[
        bool | None,
        typer.Option(
            "--manage-ufw/--no-ufw",
            help=i18n.t(
                "Enable/disable ufw allow-rule management (disable on WSL test hosts)",
                "Включить/выключить управление правилами ufw (отключайте на тестовых хостах WSL)",
            ),
        ),
    ] = None,
    inventory: Annotated[
        Path | None,
        typer.Option(
            "--inventory",
            help=i18n.t(
                "Use an existing inventory file instead of the generated one",
                "Использовать готовый inventory-файл вместо генерируемого",
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help=i18n.t(
                "Pass --check to ansible-playbook; no changes",
                "Передать --check в ansible-playbook; без изменений",
            ),
        ),
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
        typer.Option(
            "--wsl-distro",
            help=i18n.t(
                "WSL distro for local mode (default distro)",
                "Дистрибутив WSL для локального режима (по умолчанию)",
            ),
        ),
    ] = None,
    wsl_venv: Annotated[
        str,
        typer.Option(
            "--wsl-venv",
            help=i18n.t(
                "WSL venv holding ansible-playbook (local mode)",
                "WSL venv с ansible-playbook (локальный режим)",
            ),
        ),
    ] = DEFAULT_WSL_VENV,
    host: Annotated[
        str | None,
        typer.Option(
            "--host",
            "-H",
            help=i18n.t(
                "VPS host/IP (remote mode; required)",
                "Хост/IP VPS (удалённый режим; обязателен)",
            ),
        ),
    ] = None,
    user: Annotated[
        str,
        typer.Option(
            "--user", "-u", help=i18n.t("SSH user (remote mode)", "SSH-пользователь (удалённый режим)")
        ),
    ] = "root",
    port: Annotated[
        int,
        typer.Option(
            "--port", "-p", help=i18n.t("SSH port (remote mode)", "SSH-порт (удалённый режим)")
        ),
    ] = 22,
    pkey: Annotated[
        Path | None,
        typer.Option(
            "--pkey",
            help=i18n.t(
                "Path to an SSH private key (remote mode)",
                "Путь к приватному SSH-ключу (удалённый режим)",
            ),
        ),
    ] = None,
    password: Annotated[
        str | None,
        typer.Option(
            "--pass",
            help=i18n.t(
                "SSH password (remote mode; avoid, prefer --pkey)",
                "SSH-пароль (удалённый режим; не рекомендуется, лучше --pkey)",
            ),
        ),
    ] = None,
    use_inventory: Annotated[
        bool,
        typer.Option(
            "--use-inventory",
            help=i18n.t(
                "Read connection params and vars from the personal inventory.yml",
                "Читать параметры подключения и переменные из личного inventory.yml",
            ),
        ),
    ] = False,
    clients_dir: Annotated[
        Path | None,
        typer.Option(
            "--clients-dir",
            help=i18n.t(
                "Where generated client configs are saved",
                "Куда сохранять сгенерированные клиентские конфиги",
            ),
        ),
    ] = None,
    full_cleanup: Annotated[
        bool,
        typer.Option(
            "--full-cleanup",
            help=i18n.t(
                "Remote cleanup: also remove the server-side venv",
                "Уборка на сервере: удалить и серверный venv",
            ),
        ),
    ] = False,
    no_cleanup: Annotated[
        bool,
        typer.Option(
            "--no-cleanup",
            help=i18n.t(
                "Remote cleanup: keep the staging dir",
                "Уборка на сервере: сохранить staging-каталог",
            ),
        ),
    ] = False,
    ru: Annotated[
        bool,
        typer.Option(
            "--ru",
            help=i18n.t(
                "Russian interface output (prompts, messages, errors, help)",
                "Русский вывод интерфейса (промпты, сообщения, ошибки, help)",
            ),
        ),
    ] = False,
) -> None:
    """Run the deploy playbook. Local mode runs it on the current machine."""
    if ru:
        i18n.set_ru(True)
    if debug and verbose:
        typer.echo(
            i18n.t(
                "error: --debug and --verbose are mutually exclusive",
                "ошибка: --debug и --verbose взаимоисключающие",
            ),
            err=True,
        )
        raise typer.Exit(2)
    if full_cleanup and no_cleanup:
        typer.echo(
            i18n.t(
                "error: --full-cleanup and --no-cleanup are mutually exclusive",
                "ошибка: --full-cleanup и --no-cleanup взаимоисключающие",
            ),
            err=True,
        )
        raise typer.Exit(2)
    if runtime is not None and runtime not in SUPPORTED_RUNTIMES:
        typer.echo(
            i18n.t(
                f"error: --runtime must be one of {', '.join(SUPPORTED_RUNTIMES)}",
                f"ошибка: --runtime должен быть одним из {', '.join(SUPPORTED_RUNTIMES)}",
            ),
            err=True,
        )
        raise typer.Exit(2)
    if pkey is not None and password is not None:
        typer.echo(
            i18n.t(
                "error: --pkey and --pass are mutually exclusive",
                "ошибка: --pkey и --pass взаимоисключающие",
            ),
            err=True,
        )
        raise typer.Exit(2)

    mode = _resolve_execution(execution)

    if use_inventory and mode == "local":
        typer.echo(
            i18n.t(
                "error: --use-inventory applies to --execution remote only; "
                "local mode generates its own inventory",
                "ошибка: --use-inventory применим только к --execution remote; "
                "local-режим генерирует свой inventory",
            ),
            err=True,
        )
        raise typer.Exit(2)
    if inventory is not None and mode == "remote":
        typer.echo(
            i18n.t(
                "error: --inventory applies to --execution local only; "
                "remote mode reads the personal inventory.yml via --use-inventory",
                "ошибка: --inventory применим только к --execution local; "
                "remote-режим читает личный inventory.yml через --use-inventory",
            ),
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
    try:
        rc = executor.deploy(request)
    except RuntimeError as exc:
        typer.echo(i18n.t(f"error: {exc}", f"ошибка: {exc}"), err=True)
        raise typer.Exit(2) from exc
    if rc != 0:
        raise typer.Exit(rc)
    if not dry_run:
        executor.fetch_configs(request)
    typer.echo(
        i18n.t(
            f"[done] configs written to {request.resolved_clients_dir()}",
            f"[готово] конфиги записаны в {request.resolved_clients_dir()}",
        )
    )


def _swap_guard(remote: FabricRemote) -> None:
    """Low-memory guard: opt-in 1G swapfile before bootstrap (never silent)."""
    detect_mem, detect_swap = swap_status_commands()
    mem = remote.run(detect_mem, warn=True)
    swaps = remote.run(detect_swap, warn=True)
    try:
        mem_kb = int(mem.stdout.strip())
        swap_entries = int(swaps.stdout.strip())
    except ValueError:
        return
    if not swap_guard_needed(mem_kb, swap_entries):
        return
    typer.echo(
        i18n.t(
            f"[remote] low memory: {mem_kb // 1024} MB RAM and no active swap — "
            "the deploy may be OOM-killed",
            f"[remote] мало памяти: {mem_kb // 1024} МБ RAM и нет активного swap — "
            "деплой может быть убит OOM-killer",
        ),
        err=True,
    )
    if not prompts.confirm(
        i18n.t(
            "Create a 1 GB swapfile /swapfile on the server?",
            "Создать swap-файл 1 ГБ /swapfile на сервере?",
        )
    ):
        typer.echo(
            i18n.t(
                "[remote] swap-guard declined; continuing without swap",
                "[remote] swap-guard отклонён; продолжаю без swap",
            ),
            err=True,
        )
        return
    for command in swap_guard_commands():
        result = remote.run(command, warn=True)
        if result.failed:
            typer.echo(
                i18n.t(
                    f"[remote] swap-guard failed: {command}\n{result.stderr}",
                    f"[remote] swap-guard ошибка: {command}\n{result.stderr}",
                ),
                err=True,
            )
            raise typer.Exit(result.return_code or 1)
    typer.echo(
        i18n.t(
            "[remote] swapfile created and enabled (fstab entry added)",
            "[remote] swap-файл создан и включён (запись в fstab добавлена)",
        )
    )


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
                i18n.t(
                    "warning: --use-inventory overrides connection/auth flags",
                    "предупреждение: --use-inventory переопределяет флаги подключения/аутентификации",
                ),
                err=True,
            )
        try:
            connection, user_vars = parse_user_inventory(repo_root)
        except (RuntimeError, TypeError) as exc:
            typer.echo(i18n.t(f"error: {exc}", f"ошибка: {exc}"), err=True)
            raise typer.Exit(2) from exc
        problems = validate_connection(connection)
        if problems:
            typer.echo(
                i18n.t(
                    f"error: {repo_root / 'inventory.yml'} is not ready for remote deploy:",
                    f"ошибка: {repo_root / 'inventory.yml'} не готов к remote-деплою:",
                ),
                err=True,
            )
            for problem in problems:
                typer.echo(f"  - {problem}", err=True)
            typer.echo(
                i18n.t(
                    "  fill the keys under all.hosts.<host> as in inventory.yml.example",
                    "  заполните ключи в all.hosts.<host> как в inventory.yml.example",
                ),
                err=True,
            )
            raise typer.Exit(2)
        if not (
            connection.get("ansible_ssh_private_key_file")
            or connection.get("ansible_ssh_pass")
        ):
            typer.echo(
                i18n.t(
                    "note: no auth key in inventory.yml; the SSH password will be "
                    "requested at run time (or set ansible_ssh_private_key_file)",
                    "заметка: в inventory.yml нет ключа аутентификации; SSH-пароль будет "
                    "запрошен во время запуска (или укажите ansible_ssh_private_key_file)",
                ),
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
        selected = prompts.text(i18n.t("VPS host (IP or hostname)", "Хост VPS (IP или hostname)"))
        if not selected:
            typer.echo(
                i18n.t(
                    "error: --host is required in remote mode",
                    "ошибка: --host обязателен в remote-режиме",
                ),
                err=True,
            )
            raise typer.Exit(2)
        resolved_host = selected

    if resolved_pkey is not None and resolved_password is not None:
        typer.echo(
            i18n.t(
                "error: both a private key and a password are configured; use one",
                "ошибка: указаны и приватный ключ, и пароль; используйте что-то одно",
            ),
            err=True,
        )
        raise typer.Exit(2)
    if resolved_pkey is not None:
        key_path = Path(resolved_pkey).expanduser()
        if not key_path.is_file():
            typer.echo(
                i18n.t(
                    f"error: private key not found: {key_path}",
                    f"ошибка: приватный ключ не найден: {key_path}",
                ),
                err=True,
            )
            raise typer.Exit(2)
    elif resolved_password is None:
        resolved_password = getpass.getpass(i18n.t("SSH password: ", "SSH-пароль: "))

    request = DeployRequest(
        repo_root=repo_root,
        overrides=overrides,
        clients_dir=clients_dir,
        verbosity=verbosity,
        debug=debug,
    )
    if cleanup == "full-cleanup":
        typer.echo(
            i18n.t(
                "[remote] note: full-cleanup keeps the swapfile (if the swap-guard created "
                "one); remove /swapfile and its fstab line manually if not needed",
                "[remote] заметка: full-cleanup сохраняет swap-файл (если swap-guard его "
                "создал); удалите /swapfile и строку в fstab вручную, если он не нужен",
            ),
            err=True,
        )
    with FabricRemote(
        resolved_host,
        user=resolved_user,
        port=resolved_port,
        key_filename=str(key_path) if resolved_pkey else None,
        password=resolved_password,
    ) as remote:
        _swap_guard(remote)
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
    typer.echo(
        i18n.t(
            f"[preview] remote deploy to {host or '<host>'}",
            f"[превью] remote-деплой на {host or '<host>'}",
        )
    )
    typer.echo(
        i18n.t(
            "[preview] swap-guard: detect RAM/swap; if RAM < 1024 MB and no swap — "
            "offer an opt-in 1G /swapfile",
            "[превью] swap-guard: детект RAM/swap; при RAM < 1024 МБ без swap — "
            "opt-in вопрос про 1G /swapfile",
        )
    )
    for command in bootstrap_commands():
        typer.echo(f"[preview] $ {command}")
    typer.echo(i18n.t("[preview] upload tarball with (allowlist):", "[превью] загрузка tarball (allowlist):"))
    from xrayvpn.core import manifest

    for entry in manifest.allowlist_entries(repo_root):
        typer.echo(f"[preview]   {entry.name}")
    request = DeployRequest(repo_root=repo_root, overrides={}, verbosity=verbosity, debug=debug)
    typer.echo(f"[preview] $ {playbook_command(request, extra_vars)}")
    for command in cleanup_commands(cleanup):
        typer.echo(f"[preview] $ {command}")


if __name__ == "__main__":
    sys.exit(app())