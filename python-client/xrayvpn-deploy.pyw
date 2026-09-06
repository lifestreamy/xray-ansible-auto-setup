"""Double-click console launcher: `xrayvpn deploy` in local mode.

Opens a regular console window, runs the command built from COMMAND below
and keeps the window open until Enter is pressed. The package is located
through python-client/.venv when `uv sync` has been run there, otherwise
via `uv run`. The file name keeps a hyphen on purpose: a plain
`xrayvpn.pyw` would shadow the `xrayvpn` package on the Windows import
path. Keep COMMAND in sync with `xrayvpn deploy --help`:
tests/test_pyw_contract.py enforces this statically.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

COMMAND: list[str] = [
    "deploy",
    "--execution", "local",
    "--no-rotate",
    "--verbose",
]


def _launcher() -> list[str]:
    venv_python = HERE / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return [str(venv_python), "-m", "xrayvpn"]
    return ["uv", "run", "--directory", str(HERE), "xrayvpn"]


def _command_line() -> str:
    words = " ".join(f'"{word}"' for word in _launcher() + COMMAND)
    return f"{words} & pause"


def main() -> int:
    return subprocess.call(
        ["cmd", "/d", "/s", "/c", _command_line()],
        cwd=str(HERE.parent),
    )


if __name__ == "__main__":
    sys.exit(main())
