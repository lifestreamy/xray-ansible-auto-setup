"""Double-click console launcher: `xrayvpn deploy` in local mode (English UI).

Opens a console window, runs the command built from COMMAND below and keeps
the window open until Enter is pressed. The Russian variant lives next to it:
`xrayvpn-deploy-ru.pyw`. The file name keeps a hyphen on purpose: a plain
`xrayvpn.pyw` would shadow the `xrayvpn` package on the Windows import path.
Keep COMMAND in sync with `xrayvpn deploy --help`:
tests/test_pyw_contract.py enforces this statically and launches both files.
"""

from __future__ import annotations

import sys

from _pywlaunch import run

COMMAND: list[str] = [
    "deploy",
    "--execution", "local",
    "--no-rotate",
    "--verbose",
]

if __name__ == "__main__":
    sys.exit(run(COMMAND))
