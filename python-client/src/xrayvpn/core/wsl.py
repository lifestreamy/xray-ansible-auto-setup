"""WSL bridge helpers — run the playbook from Windows in local mode.

Detection uses `wsl --status` exit code only (never parses localized output).
"""

from __future__ import annotations

import os
import platform
import shlex
import subprocess
from pathlib import Path


def is_windows() -> bool:
    return platform.system() == "Windows"


def wsl_available() -> bool:
    """True when `wsl --status` exits 0 (WSL installed and usable)."""
    if not is_windows():
        return False
    try:
        result = subprocess.run(
            ["wsl.exe", "--status"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def wsl_home(distro: str | None = None) -> str:
    """Ask WSL for $HOME (needed to resolve ~-based venv paths for quoting)."""
    cmd = ["wsl.exe"]
    if distro:
        cmd += ["-d", distro]
    cmd += ["bash", "-lc", 'echo "$HOME"']
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
    return result.stdout.strip()


def to_wsl_path(path: str | Path) -> str:
    """Convert a Windows path (C:\\x\\y) to a WSL path (/mnt/c/x/y)."""
    text = os.path.normpath(str(path))
    drive, rest = os.path.splitdrive(text)
    if not drive:
        return text.replace("\\", "/")
    rest = rest.replace("\\", "/")
    return f"/mnt/{drive[0].lower()}{rest}"


def quote(text: str) -> str:
    return shlex.quote(text)


def run_script(script: str, *, distro: str | None = None) -> int:
    """Run a `bash -lc` script inside WSL (default distro or an explicit one)."""
    cmd = ["wsl.exe"]
    if distro:
        cmd += ["-d", distro]
    cmd += ["bash", "-lc", script]
    return subprocess.call(cmd)