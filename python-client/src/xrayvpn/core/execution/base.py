"""Executor protocol and shared deploy request (ADR-003: one client, two modes)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class DeployRequest:
    """Everything an executor needs to run the deploy playbook."""

    repo_root: Path
    overrides: dict[str, Any] = field(default_factory=dict)
    clients_dir: Path | None = None
    dry_run: bool = False
    verbosity: int = 0
    debug: bool = False
    inventory_path: Path | None = None

    def resolved_clients_dir(self) -> Path:
        return self.clients_dir or (self.repo_root / "downloaded-clients")


class Executor(Protocol):
    def deploy(self, request: DeployRequest) -> int: ...

    def fetch_configs(self, request: DeployRequest) -> None: ...

    def cleanup(self, request: DeployRequest) -> None: ...