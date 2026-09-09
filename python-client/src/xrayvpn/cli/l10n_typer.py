"""Russian translations for Typer/Click built-in strings (typer 0.27.x).

Typer builds `--help` at import time and hard-codes its built-ins in
English. `apply_ru()` patches the finite set of user-visible strings once
per process; it must run before the app is created (see `i18n.preinit`).
The dependency is pinned to typer <0.28: the patches touch private
internals, and the pin plus tests/test_i18n.py bound the drift.

Reachability on the current CLI surface — live and test-guarded: panel
titles, RICH_HELP, DEFAULT_STRING, the Usage prefix, the help-option text,
NoSuchOption/BadParameter/UsageError messages, translate_message maps, and
the plain-text show() fallbacks (rich normally routes errors around them;
unit-tested by direct call). Defensive forward-compat, unreachable today:
ARGUMENTS_PANEL_TITLE and REQUIRED_LONG_STRING (no positional/required
params), MissingParameter and FileError messages (same reason), and
_TYPE_NAMES entries beyond int/integer/UUID.
"""

from __future__ import annotations

import re

_PATCHED = False

_EXTRA_ARGS = re.compile(r"^Got unexpected extra argument\(s\) \((?P<args>.*)\)$")
_REQUIRES_ARG = re.compile(
    r"^Option (?P<opt>'[^']+') requires (?P<what>an argument\.|\d+ arguments\.)$"
)
_NO_VALUE = re.compile(r"^Option (?P<opt>'[^']+') does not take a value\.$")
_NOT_VALID_BOOL = re.compile(
    r"^(?P<value>.+) is not a valid boolean\. Recognized values: (?P<states>.*)$"
)
_NOT_VALID = re.compile(r"^(?P<value>.+) is not a valid (?P<type>[A-Za-z ]+)\.$")

_TYPE_NAMES = {
    "integer": "целым числом",
    "int": "целым числом",
    "float": "числом",
    "number": "числом",
    "boolean": "логическим значением",
    "bool": "логическим значением",
    "uuid": "UUID",
    "path": "путём",
    "file": "файлом",
    "directory": "каталогом",
    "text": "текстом",
    "string": "строкой",
}


def translate_message(message: str) -> str:
    """Map the hard-coded English parser/type messages onto Russian."""
    match = _EXTRA_ARGS.match(message)
    if match:
        return f"Получены неожиданные лишние аргументы ({match['args']})"
    match = _REQUIRES_ARG.match(message)
    if match:
        what = "аргумент" if match["what"] == "an argument." else "аргументов: " + match["what"].split()[0]
        return f"Опция {match['opt']} требует {what}."
    match = _NO_VALUE.match(message)
    if match:
        return f"Опция {match['opt']} не принимает значение."
    match = _NOT_VALID_BOOL.match(message)
    if match:
        return (
            f"{match['value']} не является допустимым логическим значением. "
            f"Допустимые значения: {match['states']}"
        )
    match = _NOT_VALID.match(message)
    if match:
        kind = _TYPE_NAMES.get(match["type"].lower())
        if kind:
            return f"{match['value']} не является допустимым {kind}."
        return f"{match['value']} — недопустимое значение ({match['type']})."
    return message


def apply_ru() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    from typer import rich_utils
    from typer._click import decorators as click_decorators
    from typer._click import exceptions as click_exceptions
    from typer._click import formatting as click_formatting

    rich_utils.ARGUMENTS_PANEL_TITLE = "Аргументы"
    rich_utils.OPTIONS_PANEL_TITLE = "Опции"
    rich_utils.COMMANDS_PANEL_TITLE = "Команды"
    rich_utils.ERRORS_PANEL_TITLE = "Ошибка"
    rich_utils.ABORTED_TEXT = "Прервано."
    rich_utils.DEFAULT_STRING = "[по умолчанию: {}]"
    rich_utils.REQUIRED_LONG_STRING = "[обязательно]"
    rich_utils.RICH_HELP = "Попробуйте [blue]'{command_path} {help_option}'[/] для справки."

    original_write_usage = click_formatting.HelpFormatter.write_usage

    def write_usage(self, prog, args="", prefix=None):  # type: ignore[no-untyped-def]
        if prefix is None:
            prefix = "Использование: "
        original_write_usage(self, prog, args, prefix)

    click_formatting.HelpFormatter.write_usage = write_usage

    original_help_option = click_decorators.help_option

    def help_option(param_decls):  # type: ignore[no-untyped-def]
        decorate = original_help_option(param_decls)

        def apply(command):  # type: ignore[no-untyped-def]
            decorate(command)
            command.params[-1].help = "Показать это сообщение и выйти."
            return command

        return apply

    click_decorators.help_option = help_option

    def click_exception_show(self, file=None):  # type: ignore[no-untyped-def]
        if file is None:
            file = click_exceptions.get_text_stderr()
        click_exceptions.echo(
            f"Ошибка: {self.format_message()}", file=file, color=self.show_color
        )

    click_exceptions.ClickException.show = click_exception_show

    def usage_error_show(self, file=None):  # type: ignore[no-untyped-def]
        if file is None:
            file = click_exceptions.get_text_stderr()
        color = None
        hint = ""
        if self.ctx is not None and self.ctx.command.get_help_option(self.ctx) is not None:
            command = self.ctx.command_path
            option = self.ctx.help_option_names[0]
            hint = f"Попробуйте '{command} {option}' для справки.\n"
        if self.ctx is not None:
            color = self.ctx.color
            click_exceptions.echo(
                f"{self.ctx.get_usage()}\n{hint}", file=file, color=color
            )
        click_exceptions.echo(
            f"Ошибка: {self.format_message()}", file=file, color=color
        )

    click_exceptions.UsageError.show = usage_error_show

    def usage_error_format_message(self):  # type: ignore[no-untyped-def]
        return translate_message(self.message)

    click_exceptions.UsageError.format_message = usage_error_format_message

    def bad_parameter_format_message(self):  # type: ignore[no-untyped-def]
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)
        else:
            return f"Неверное значение: {translate_message(self.message)}"
        hint = click_exceptions._join_param_hints(param_hint)
        return f"Неверное значение для {hint}: {translate_message(self.message)}"

    click_exceptions.BadParameter.format_message = bad_parameter_format_message

    def missing_parameter_format_message(self):  # type: ignore[no-untyped-def]
        if self.param_hint is not None:
            param_hint = self.param_hint
        elif self.param is not None:
            param_hint = self.param.get_error_hint(self.ctx)
        else:
            param_hint = None
        param_hint = click_exceptions._join_param_hints(param_hint)
        param_hint = f" {param_hint}" if param_hint else ""

        param_type = self.param_type
        if param_type is None and self.param is not None:
            param_type = self.param.param_type_name

        msg = self.message
        if self.param is not None:
            msg_extra = self.param.type.get_missing_message(param=self.param, ctx=self.ctx)
            if msg_extra:
                msg = f"{msg}. {msg_extra}" if msg else msg_extra
        msg = f" {msg}" if msg else ""

        missing = {
            "argument": "Отсутствует аргумент",
            "option": "Отсутствует опция",
            "parameter": "Отсутствует параметр",
        }.get(param_type, f"Отсутствует {param_type}")
        return f"{missing}{param_hint}.{msg}"

    click_exceptions.MissingParameter.format_message = missing_parameter_format_message

    def no_such_option_format_message(self):  # type: ignore[no-untyped-def]
        base = f"Нет такой опции: {self.option_name}"
        if not self.possibilities:
            return base
        possibility_str = ", ".join(sorted(self.possibilities))
        return f"{base} (Возможные варианты: {possibility_str})"

    click_exceptions.NoSuchOption.format_message = no_such_option_format_message

    def file_error_format_message(self):  # type: ignore[no-untyped-def]
        return f"Не удалось открыть файл {self.ui_filename!r}: {self.message}"

    click_exceptions.FileError.format_message = file_error_format_message
