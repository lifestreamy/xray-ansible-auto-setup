"""Interactive REPL session: type once, run deploy several times.

Entered by running xrayvpn with no arguments on a TTY (or `xrayvpn repl`,
or the selftest env for CI smoke feeds). Built-in commands are handled
here; anything else is dispatched through the real Typer app in-process
(`app(args=...)`, not CliRunner — click's input isolation would kill the
InquirerPy prompts of a deploy). The built-in typer `--help` language is
fixed at process start; every runtime string and click error follows
`lang ru|en` in both directions.
"""

from __future__ import annotations

import ctypes
import os
import shlex
import sys
from collections.abc import Callable, Mapping, Sequence

from xrayvpn import __version__, i18n
from xrayvpn.cli import l10n_typer, prompts

REPL_SELFTEST_ENV = "XRAYVPN_REPL_SELFTEST"
PROMPT = "> "
_PREFIX_ALIASES = {"xrayvpn", "xrayvpn.exe"}
_LANG_ALIASES = {
    "ru": "ru",
    "рус": "ru",
    "русский": "ru",
    "en": "en",
    "англ": "en",
    "english": "en",
}
_EXIT_WORDS = {"exit", "quit", "q"}


def session_requested() -> bool:
    """No-args start opens the session on a TTY; the selftest env removes the gate."""
    return prompts.is_interactive() or _selftest_enabled()


def _selftest_enabled() -> bool:
    return os.environ.get(REPL_SELFTEST_ENV) == "1"


def locale_suggests_ru(
    *,
    env: Mapping[str, str] | None = None,
    platform: str | None = None,
    win_ui_lang: Callable[[], int] | None = None,
) -> bool:
    """POSIX: first set of LC_ALL/LC_MESSAGES/LANG, `ru*` wins; win32: the primary
    UI language is 0x19. Everything else (and any error) is English."""
    environment = os.environ if env is None else env
    sys_platform = sys.platform if platform is None else platform
    if sys_platform == "win32":
        getter = win_ui_lang or _win_default_ui_language
        try:
            return (getter() & 0x3FF) == 0x19
        except Exception:  # noqa: BLE001 - detection must never break the start
            return False
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = (environment.get(key) or "").strip().lower()
        if value:
            return value.startswith("ru")
    return False


def _win_default_ui_language() -> int:
    return int(ctypes.windll.kernel32.GetUserDefaultUILanguage())  # type: ignore[attr-defined]


def set_session_lang(lang: str) -> None:
    """Runtime language switch: i18n strings + typer/Click patches both ways."""
    i18n.set_lang(lang)
    if lang == "ru":
        l10n_typer.apply_ru()
    else:
        l10n_typer.revert_ru()


def normalize_lang(value: str) -> str | None:
    return _LANG_ALIASES.get(value.strip().lower())


def tokenize(line: str) -> list[str]:
    """posix=False keeps Windows backslashes intact; quotes are unwrapped after."""
    return [_clean_token(token) for token in shlex.split(line, posix=False)]


def _clean_token(token: str) -> str:
    unwrapped = _unwrap(token)
    if unwrapped is not None:
        return unwrapped
    if "=" in token:
        name, _, value = token.partition("=")
        unwrapped = _unwrap(value)
        if unwrapped is not None:
            return f"{name}={unwrapped}"
    return token


def _unwrap(token: str) -> str | None:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("\"", "'"):
        return token[1:-1]
    return None


def _box(lines: list[str]) -> str:
    width = max(len(line) for line in lines) + 2
    top = "+" + "-" * width + "+"
    body = "\n".join(f"| {line.ljust(width - 2)} |" for line in lines)
    return f"{top}\n{body}\n{top}"


def lang_notice() -> str:
    """One-line confirmation in the NEW language; the welcome box prints once."""
    return i18n.t("interface language: English", "язык интерфейса: русский")


def welcome_screen(version: str = __version__) -> str:
    """Screen 0: what this does, the just-start path, and the language threshold."""
    threshold = i18n.t(
        "type RU — русский интерфейс",
        "type EN — English interface",
    )
    title = i18n.t(
        "xrayvpn — VPN server provisioning assistant",
        "xrayvpn — помощник развёртывания VPN-сервера",
    )
    purpose = i18n.t(
        "Deploys a self-hosted Xray VLESS + REALITY VPN server on a remote VPS.",
        "Разворачивает собственный VPN-сервер Xray VLESS + REALITY на удалённом VPS.",
    )
    start_line = i18n.t("Just start:", "Просто начни:")
    keys = i18n.t(
        "help — command list   deploy --help — all flags   version — version   exit — leave",
        "help — список команд   deploy --help — все флаги   version — версия   exit — выход",
    )
    return _box([title, f"v{version}", purpose, "", start_line, "  deploy", "", keys, "", threshold])


def short_hint() -> str:
    return i18n.t(
        'type "deploy" to start, "help" for the command list, "exit" to leave',
        'введите "deploy" чтобы начать, "help" — список команд, "exit" — выход',
    )


def help_text() -> str:
    """Dynamic command reference (t() at call time, unlike baked typer help)."""
    return "\n".join(
        [
            i18n.t("commands:", "команды:"),
            i18n.t(
                "  deploy [flags]   same syntax as: xrayvpn deploy --help",
                "  deploy [флаги]   тот же синтаксис, что у xrayvpn deploy --help",
            ),
            i18n.t(
                "  service status|restart|logs|reboot --help — recovery actions",
                "  service status|restart|logs|reboot --help — диагностика и восстановление",
            ),
            i18n.t(
                "  lang ru|en       switch interface language now (рус/англ ok)",
                "  lang ru|en       переключить язык интерфейса (рус/англ тоже)",
            ),
            i18n.t("  help             this list", "  help             этот список"),
            i18n.t("  version          show version", "  version          показать версию"),
            i18n.t(
                "  exit|quit|q      leave (Ctrl+D works too)",
                "  exit|quit|q      выход (или Ctrl+D)",
            ),
            "",
            i18n.t(
                "note: the built-in --help language is fixed at process start (--ru / XRAYVPN_LANG).",
                "заметка: язык встроенного --help фиксируется при запуске процесса "
                "(--ru / XRAYVPN_LANG).",
            ),
        ]
    )


def start(
    dispatch: Callable[[list[str]], int],
    *,
    version: str = __version__,
    update_hint: Callable[[], str | None] | None = None,
) -> int:
    """Session loop; the process exit code is the last dispatched command's rc."""
    explicit_lang = (os.environ.get(i18n.LANG_ENV) or "").strip()
    if not explicit_lang and not i18n.is_ru() and locale_suggests_ru():
        set_session_lang("ru")
    print(welcome_screen(version))
    if update_hint is not None:
        hint = update_hint()
        if hint:
            print(hint)
    last_rc = 0
    while True:
        try:
            line = input(PROMPT)
        except EOFError:
            print()
            return last_rc
        except KeyboardInterrupt:
            print()
            print(i18n.t(
                'type "exit" or press Ctrl+D to leave',
                'введите "exit" или нажмите Ctrl+D для выхода',
            ))
            continue
        tokens = tokenize(line)
        if tokens and tokens[0].lower() in _PREFIX_ALIASES:
            tokens = tokens[1:]
        if not tokens:
            print(short_hint())
            continue
        if len(tokens) == 1:
            lang = normalize_lang(tokens[0])
            if lang is not None:
                set_session_lang(lang)
                print(lang_notice())
                continue
        command = tokens[0].lower()
        if command in _EXIT_WORDS:
            return last_rc
        options = {token.lower() for token in tokens}
        if all(token.startswith("-") for token in options):
            if "--ru" in options:
                set_session_lang("ru")
                print(lang_notice())
            if "--version" in options:
                print(f"xrayvpn {version}")
            unknown = options - {"--ru", "--version"}
            if unknown:
                joined = ", ".join(sorted(unknown))
                print(
                    i18n.t(
                        f"unknown option: {joined} (help — command list)",
                        f"неизвестная опция: {joined} (help — список команд)",
                    )
                )
            continue
        try:
            if command == "help":
                print(help_text())
            elif command == "version":
                print(f"xrayvpn {version}")
            elif command == "lang":
                _switch_lang(tokens[1:])
            elif command == "repl":
                print(i18n.t(
                    "[session] you are already in a session",
                    "[сессия] вы уже в сессии",
                ))
            else:
                last_rc = dispatch(tokens)
                if last_rc == 130:
                    print(i18n.t(
                        "[cancel] command aborted; the session continues",
                        "[отмена] команда прервана; сессия продолжает работу",
                    ))
                    last_rc = 0
        except KeyboardInterrupt:
            print(i18n.t(
                "[interrupted] command aborted; the session continues",
                "[прервано] команда остановлена; сессия продолжает работу",
            ))


def _switch_lang(args: Sequence[str]) -> None:
    lang = normalize_lang(args[0]) if args else None
    if lang is None:
        print(i18n.t("usage: lang ru|en", "использование: lang ru|en"))
        return
    set_session_lang(lang)
    print(lang_notice())
