"""Static contract: the argv baked into xrayvpn-deploy.pyw must exist in the CLI.

Guards against the launcher drifting away from the Typer surface (a renamed
command or a dropped flag has to fail here, not on double-click).
"""

from __future__ import annotations

import ast
from pathlib import Path

import typer.main

from xrayvpn.cli.main import EXECUTION_MODES, app

PYW_PATH = Path(__file__).resolve().parents[1] / "xrayvpn-deploy.pyw"


def _pyw_command() -> list[str]:
    """Extract the literal COMMAND list from the .pyw without executing it."""
    tree = ast.parse(PYW_PATH.read_text(encoding="utf-8"), filename=str(PYW_PATH))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "COMMAND":
                if not isinstance(value, ast.List):
                    raise AssertionError("COMMAND must be a list literal")
                elements = value.elts
                words = [
                    el.value
                    for el in elements
                    if isinstance(el, ast.Constant) and isinstance(el.value, str)
                ]
                assert len(words) == len(elements), "COMMAND must hold only string literals"
                return words
    raise AssertionError("COMMAND literal list not found in xrayvpn.pyw")


def _cli_registry() -> dict[str, set[str]]:
    """command name -> every flag spelling the CLI accepts for it."""
    group = typer.main.get_command(app)
    registry: dict[str, set[str]] = {}
    for name, command in group.commands.items():
        flags: set[str] = set()
        for param in command.params:
            flags.update(param.opts)
            flags.update(getattr(param, "secondary_opts", []))
        registry[name] = flags
    return registry


def test_pyw_exists_and_parses() -> None:
    assert PYW_PATH.is_file(), "xrayvpn.pyw launcher is missing"
    _pyw_command()


def test_pyw_invokes_a_real_command() -> None:
    command = _pyw_command()
    assert command, "COMMAND must not be empty"
    registry = _cli_registry()
    assert command[0] in registry, (
        f"xrayvpn.pyw calls unknown command {command[0]!r}; "
        f"CLI defines {sorted(registry)}"
    )


def test_pyw_flags_exist_in_cli() -> None:
    command = _pyw_command()
    flags = _cli_registry()[command[0]]
    used = [word for word in command if word.startswith("-")]
    assert used, "the launcher must pin its mode/flags explicitly"
    unknown = [word for word in used if word not in flags]
    assert not unknown, f"xrayvpn.pyw uses flags absent from the CLI: {unknown}"


def test_pyw_execution_mode_is_valid() -> None:
    command = _pyw_command()
    if "--execution" in command:
        value = command[command.index("--execution") + 1]
        assert value in EXECUTION_MODES, f"bad --execution value: {value!r}"
