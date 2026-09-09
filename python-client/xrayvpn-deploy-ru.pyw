"""Двойной клик: `xrayvpn deploy` в локальном режиме (русский интерфейс).

Открывает консоль, выполняет команду из COMMAND ниже и держит окно открытым
до нажатия Enter. Английский вариант — рядом: `xrayvpn-deploy.pyw`. Дефис в
имени обязателен: обычный `xrayvpn.pyw` перехватывал бы `import xrayvpn` на
Windows. Синхронность COMMAND с `xrayvpn deploy --help` контролирует
tests/test_pyw_contract.py (статически и реальным запуском обоих файлов).
"""

from __future__ import annotations

import sys

from _pywlaunch import run

COMMAND: list[str] = [
    "deploy",
    "--execution", "local",
    "--no-rotate",
    "--verbose",
    "--ru",
]

if __name__ == "__main__":
    sys.exit(run(COMMAND, ru=True))
