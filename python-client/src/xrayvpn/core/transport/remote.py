"""SSH transport abstraction (ADR-009).

`Remote` is the protocol consumed by business logic; `FabricRemote` is the
default implementation on top of Fabric/paramiko. Host-key policy mirrors the
shell clients' `StrictHostKeyChecking=no` (AutoAddPolicy) — a stated trade-off.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Self

import paramiko
from fabric import Connection


@dataclass
class CommandResult:
    """Normalized view of a remote command outcome."""

    return_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def failed(self) -> bool:
        return self.return_code != 0


class Remote(Protocol):
    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        warn: bool = True,
        env: dict[str, str] | None = None,
    ) -> CommandResult: ...

    def put(self, local: str | Path, remote: str) -> None: ...

    def get(self, remote: str, local: str | Path) -> None: ...

    def close(self) -> None: ...


class FabricRemote:
    """Fabric-backed Remote. Connects lazily on first use (context manager)."""

    def __init__(
        self,
        host: str,
        *,
        user: str = "root",
        port: int = 22,
        key_filename: str | None = None,
        password: str | None = None,
        connect_timeout: int = 15,
    ) -> None:
        connect_kwargs: dict[str, str] = {}
        if password is not None:
            connect_kwargs["password"] = password
        if key_filename is not None:
            connect_kwargs["key_filename"] = str(Path(key_filename).expanduser())
        self._conn = Connection(
            host=host,
            user=user,
            port=port,
            connect_timeout=connect_timeout,
            connect_kwargs=connect_kwargs or None,
        )
        self._open = False

    def _ensure_open(self) -> None:
        if not self._open:
            self._conn.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.open()
            self._open = True

    def run(
        self,
        command: str,
        *,
        sudo: bool = False,
        warn: bool = True,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        self._ensure_open()
        runner = self._conn.sudo if sudo else self._conn.run
        result = runner(command, warn=warn, env=env)
        return CommandResult(
            return_code=result.exited,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    def put(self, local: str | Path, remote: str) -> None:
        self._ensure_open()
        self._conn.put(str(local), remote)

    def get(self, remote: str, local: str | Path) -> None:
        self._ensure_open()
        self._conn.get(remote, str(local))

    def close(self) -> None:
        if self._open:
            self._conn.close()
            self._open = False

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()