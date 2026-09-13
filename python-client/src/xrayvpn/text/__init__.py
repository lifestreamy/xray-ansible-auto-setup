"""User-facing string catalog: key → (EN, RU).

Single source for client UI text (rule in `.kilo/rules` gate after v0.4.x): no
user-visible literals outside this module; call sites use `i18n.t(KEY, **fmt)`.
Templates interpolate via `{param}` markers; `{value!r}` conversions allowed.
`xrayvpn/i18n.py` is the mechanism (language state); this package is the data.
"""

from __future__ import annotations

from typing import Final, NamedTuple


class Entry(NamedTuple):
    en: str
    ru: str


MESSAGES: Final[dict[str, Entry]] = {
    # --- shared prompts and error envelope ---
    "COMMON_HOST_PROMPT": Entry(
        "VPS host (IP or hostname)", "Хост VPS (IP или hostname)"
    ),
    "COMMON_SSH_PASS_PROMPT": Entry("SSH password: ", "SSH-пароль: "),
    "COMMON_ERR": Entry("error: {err}", "ошибка: {err}"),
    "COMMON_USER": Entry("SSH user", "SSH-пользователь"),
    "COMMON_PORT": Entry("SSH port", "SSH-порт"),
    "COMMON_PKEY": Entry(
        "Path to an SSH private key", "Путь к приватному SSH-ключу"
    ),
    "COMMON_PASS": Entry(
        "SSH password (avoid, prefer --pkey)",
        "SSH-пароль (не рекомендуется, лучше --pkey)",
    ),
    # --- core: executors and update check ---
    "EXEC_BOOTSTRAP_FAIL": Entry(
        "[remote] bootstrap failed: {command}\n{err}",
        "[remote] ошибка bootstrap: {command}\n{err}",
    ),
    "EXEC_EXTRACT_FAIL": Entry(
        "[remote] extract failed:\n{err}",
        "[remote] ошибка распаковки:\n{err}",
    ),
    "EXEC_PLAYBOOK_FAIL": Entry(
        "[remote] playbook failed (rc={rc})",
        "[remote] ошибка playbook (rc={rc})",
    ),
    "EXEC_FETCHED": Entry("[remote] fetched {name}", "[remote] получен {name}"),
    "EXEC_UPDATE_AVAILABLE": Entry(
        "update available: {tag} — {page}",
        "доступно обновление: {tag} — {page}",
    ),
    "I18N_LANG_WARNING": Entry(
        "warning: unknown {env} value {value!r}; falling back to English",
        "предупреждение: неизвестное значение {env} {value!r}; переключаюсь на английский",
    ),
    # --- interactive session (repl) ---
    "REPL_LANG_NOTICE": Entry(
        "interface language: English", "язык интерфейса: русский"
    ),
    "REPL_WELCOME_THRESHOLD": Entry(
        "type RU — русский интерфейс", "type EN — English interface"
    ),
    "REPL_WELCOME_TITLE": Entry(
        "xrayvpn — VPN server provisioning assistant",
        "xrayvpn — помощник развёртывания VPN-сервера",
    ),
    "REPL_WELCOME_PURPOSE": Entry(
        "Deploys a self-hosted Xray VLESS + REALITY VPN server on a remote VPS.",
        "Разворачивает собственный VPN-сервер Xray VLESS + REALITY на удалённом VPS.",
    ),
    "REPL_WELCOME_START": Entry("Just start:", "Просто начни:"),
    "REPL_WELCOME_KEYS": Entry(
        "help — command list   deploy --help — all flags   version — version   exit — leave",
        "help — список команд   deploy --help — все флаги   version — версия   exit — выход",
    ),
    "REPL_SHORT_HINT": Entry(
        'type "deploy" to start, "help" for the command list, "exit" to leave',
        'введите "deploy" чтобы начать, "help" — список команд, "exit" — выход',
    ),
    "REPL_HELP_HEADER": Entry("commands:", "команды:"),
    "REPL_HELP_DEPLOY": Entry(
        "  deploy [flags]   same syntax as: xrayvpn deploy --help",
        "  deploy [флаги]   тот же синтаксис, что у xrayvpn deploy --help",
    ),
    "REPL_HELP_SERVICE": Entry(
        "  service status|restart|logs|reboot --help — recovery actions",
        "  service status|restart|logs|reboot --help — диагностика и восстановление",
    ),
    "REPL_HELP_LANG": Entry(
        "  lang ru|en       switch interface language now (рус/англ ok)",
        "  lang ru|en       переключить язык интерфейса (рус/англ тоже)",
    ),
    "REPL_HELP_HELP": Entry("  help             this list", "  help             этот список"),
    "REPL_HELP_VERSION": Entry(
        "  version          show version", "  version          показать версию"
    ),
    "REPL_HELP_EXIT": Entry(
        "  exit|quit|q      leave (Ctrl+D works too)",
        "  exit|quit|q      выход (или Ctrl+D)",
    ),
    "REPL_HELP_NOTE": Entry(
        "note: the built-in --help language is fixed at process start (--ru / XRAYVPN_LANG).",
        "заметка: язык встроенного --help фиксируется при запуске процесса (--ru / XRAYVPN_LANG).",
    ),
    "REPL_KI_TIP": Entry(
        'type "exit" or press Ctrl+D to leave',
        'введите "exit" или нажмите Ctrl+D для выхода',
    ),
    "REPL_UNKNOWN_OPT": Entry(
        "unknown option: {opts} (help — command list)",
        "неизвестная опция: {opts} (help — список команд)",
    ),
    "REPL_ALREADY": Entry(
        "[session] you are already in a session", "[сессия] вы уже в сессии"
    ),
    "REPL_ABORTED": Entry(
        "[cancel] command aborted; the session continues",
        "[отмена] команда прервана; сессия продолжает работу",
    ),
    "REPL_INTERRUPTED": Entry(
        "[interrupted] command aborted; the session continues",
        "[прервано] команда остановлена; сессия продолжает работу",
    ),
    "REPL_LANG_USAGE": Entry("usage: lang ru|en", "использование: lang ru|en"),
    # --- service command ---
    "SVC_HELP": Entry(
        "Service status and point recovery over SSH (target is always the VPS).",
        "Состояние сервиса и точечное восстановление по SSH (цель всегда VPS).",
    ),
    "SVC_HOST_OPT": Entry("VPS host/IP", "Хост/IP VPS"),
    "SVC_INVENTORY_OPT": Entry(
        "Read connection params from the personal inventory.yml",
        "Читать параметры подключения из личного inventory.yml",
    ),
    "SVC_RU_OPT": Entry("Russian interface output", "Русский вывод интерфейса"),
    "SVC_NOINT_OPT": Entry(
        "Never prompt (CI/scripts)", "Никогда не спрашивать (CI/скрипты)"
    ),
    "SVC_SINCE_OPT": Entry(
        "journal window for the dump: 30m | 24h | 7d (default 24h)",
        "окно дампа журнала: 30m | 24h | 7d (по умолчанию 24h)",
    ),
    "SVC_OUT_OPT": Entry(
        "where to save the dump (file or folder; default <workspace>/logs/)",
        "куда сохранить дамп (файл или папка; по умолчанию <workspace>/logs/)",
    ),
    "SVC_YES_OPT": Entry(
        "required confirmation: the host reboot really happens",
        "обязательное подтверждение: reboot хоста реально выполнится",
    ),
    "SVC_SINCE_INVALID": Entry(
        "invalid --since {value!r} (expected like 30m, 24h, 7d)",
        "неверный --since {value!r} (ожидаётся формат вроде 30m, 24h, 7d)",
    ),
    "SVC_STATUS_TITLE": Entry(
        "service xray@{host}:{port} — {active}",
        "сервис xray@{host}:{port} — {active}",
    ),
    "SVC_STATUS_FACTS": Entry(
        "restarts(NRestarts)={n} since={since} sub={sub}",
        "рестартов(NRestarts)={n} с={since} под={sub}",
    ),
    "SVC_STATUS_STORM": Entry(
        "outbound errors in the last 30 min: {count}",
        "ошибок исходящего за последние 30 мин: {count}",
    ),
    "SVC_JOURNAL_TAIL": Entry("journal tail:", "хвост журнала:"),
    "SVC_LISTENERS": Entry("listeners:", "слушатели:"),
    "SVC_MEMORY": Entry("memory:", "память:"),
    "SVC_RESTARTED": Entry(
        "[done] xray restarted ({state}); clients reconnect in 10-15s",
        "[готово] xray перезапущен ({state}); клиенты переподключатся за 10-15 с",
    ),
    "SVC_LOGS_SAVED": Entry(
        "[done] journal ({since}) saved to {path}",
        "[готово] журнал ({since}) сохранён в {path}",
    ),
    "SVC_REBOOT_NEED_YES": Entry(
        "error: a full host reboot is a last resort (see docs/RUNBOOK first);"
        " rerun with --yes to confirm",
        "ошибка: полный reboot хоста — крайнее средство (сначала docs/RUNBOOK);"
        " повторите с --yes для подтверждения",
    ),
    "SVC_REBOOTING": Entry(
        "[ok] host {host} is rebooting; the VPN comes up with systemd (allow a minute)",
        "[ок] хост {host} перезагружается; VPN поднимется вместе с systemd (минута)",
    ),
}
