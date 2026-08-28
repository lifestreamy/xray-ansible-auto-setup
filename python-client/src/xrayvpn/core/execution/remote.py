"""RemoteExecutor — provision a VPS over SSH (ADR-001 semantics).

Flow: idempotent bootstrap (venv + pinned ansible-core + collection cache) →
tarball upload from the allowlist manifest → server-side inventory (0600) →
ansible-playbook on the server → SFTP fetch of generated client configs →
cleanup per mode. No dependency on GitHub or on the shell clients.
"""

from __future__ import annotations

import shlex
import tempfile
from pathlib import Path

from xrayvpn.core import manifest
from xrayvpn.core.execution.base import DeployRequest, extra_var_args
from xrayvpn.core.inventory import build_inventory
from xrayvpn.core.transport.remote import Remote

ANSIBLE_CORE_PIN = "2.21.3"
SERVER_VENV = "/opt/xrayvpn-venv"
# Staging lives in /tmp: the SFTP user must be able to write it (a non-root
# SSH user cannot write /opt). The playbook itself runs with become anyway.
SERVER_STAGING = "/tmp/xrayvpn"
SERVER_COLLECTIONS = f"{SERVER_VENV}/collections"
SERVER_FETCH_DIR = f"{SERVER_STAGING}/fetch"
CONFIG_SOURCE = "/root/vpn-configs"


def bootstrap_commands() -> list[str]:
    """Idempotent server preparation (venv cached between runs).

    Privileged steps run through `sudo -n` (no-op when the SSH user is root;
    passwordless sudo is required otherwise).
    """
    return [
        "python3 -V",
        f"sudo -n [ -x {SERVER_VENV}/bin/python ] || sudo -n python3 -m venv {SERVER_VENV}",
        f"sudo -n {SERVER_VENV}/bin/pip install -q ansible-core=={ANSIBLE_CORE_PIN}",
        (
            f"sudo -n [ -d {SERVER_COLLECTIONS}/ansible_collections/community/general ] || "
            f"sudo -n {SERVER_VENV}/bin/ansible-galaxy collection install community.general "
            f"-p {SERVER_COLLECTIONS}"
        ),
        f"mkdir -p {SERVER_STAGING} {SERVER_FETCH_DIR}",
    ]


def playbook_command(request: DeployRequest, extra_vars: dict[str, object]) -> str:
    """The ansible-playbook invocation on the server (collections from the venv)."""
    parts = [
        "cd",
        SERVER_STAGING,
        "&&",
        f"ANSIBLE_COLLECTIONS_PATH={SERVER_COLLECTIONS}",
        f"{SERVER_VENV}/bin/ansible-playbook",
        "-i",
        "inventory.yml",
        "deploy.yml",
    ]
    if request.verbosity >= 4:
        parts.append("-vvvv")
    elif request.verbosity == 3:
        parts.append("-vvv")
    if request.debug:
        parts += ["-e", "xray_debug=true"]
    # JSON extra-var: one -e with a shell-quoted JSON object (types preserved).
    flag, payload = extra_var_args(extra_vars)
    parts += [flag, shlex.quote(payload)]
    if request.dry_run:
        parts.append("--check")
    return " ".join(parts)


def cleanup_commands(mode: str) -> list[str]:
    """Cleanup semantics: cleanup keeps the venv cache; full-cleanup removes it."""
    if mode == "full-cleanup":
        return [f"rm -rf {SERVER_STAGING} {SERVER_VENV}"]
    if mode == "no-cleanup":
        return []
    return [f"rm -rf {SERVER_STAGING}"]


def fetch_targets(listing: str) -> list[str]:
    """Filter an `ls` listing down to client config files (.json/.yaml)."""
    targets: list[str] = []
    for line in listing.splitlines():
        name = line.strip()
        if name.endswith((".json", ".yaml")):
            targets.append(name)
    return targets


class RemoteExecutor:
    """Orchestrates bootstrap → upload → run → fetch → cleanup over a Remote."""

    def __init__(self, remote: Remote, *, cleanup: str = "cleanup") -> None:
        self._remote = remote
        self.cleanup = cleanup

    def deploy(self, request: DeployRequest, extra_vars: dict[str, object]) -> int:
        for command in bootstrap_commands():
            result = self._remote.run(command, warn=True)
            if result.failed:
                print(f"[remote] bootstrap failed: {command}\n{result.stderr}")
                return result.return_code

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)

            bundle = temp / "bundle.tar.gz"
            manifest.build_tarball(request.repo_root, bundle)
            self._remote.put(bundle, f"{SERVER_STAGING}/bundle.tar.gz")
            extract = (
                f"tar -xzf {SERVER_STAGING}/bundle.tar.gz -C {SERVER_STAGING} "
                f"&& rm -f {SERVER_STAGING}/bundle.tar.gz"
            )
            result = self._remote.run(extract, warn=True)
            if result.failed:
                print(f"[remote] extract failed:\n{result.stderr}")
                return result.return_code

            inv = temp / "inventory.yml"
            inv.write_text(
                build_inventory(
                    {},
                    connection="local",
                    python_interpreter=f"{SERVER_VENV}/bin/python",
                ),
                encoding="utf-8",
            )
            self._remote.put(inv, f"{SERVER_STAGING}/inventory.yml")
            self._remote.run(f"chmod 0600 {SERVER_STAGING}/inventory.yml")

            result = self._remote.run(playbook_command(request, extra_vars), warn=True)
            if result.failed:
                print(f"[remote] playbook failed (rc={result.return_code})")
                return result.return_code

        if not request.dry_run:
            self.fetch_configs(request.resolved_clients_dir())

        for command in cleanup_commands(self.cleanup):
            self._remote.run(command, warn=True)
        return 0

    def fetch_configs(self, clients_dir: Path) -> None:
        """Stage the generated configs via sudo, then download them by SFTP."""
        clients_dir.mkdir(parents=True, exist_ok=True)
        # Glob must expand INSIDE sudo (the SSH user cannot read /root/vpn-configs);
        # root's umask may deny reads, so grant explicit world-read access.
        prepare = (
            f"sudo -n bash -c 'mkdir -p {SERVER_FETCH_DIR} && "
            f"cp {CONFIG_SOURCE}/*.json {CONFIG_SOURCE}/*.yaml {SERVER_FETCH_DIR}/ "
            f"2>/dev/null && chmod -R a+rX {SERVER_FETCH_DIR} || true'"
        )
        self._remote.run(prepare, warn=True)
        listing = self._remote.run(f"ls {SERVER_FETCH_DIR}", warn=True)
        for name in fetch_targets(listing.stdout):
            remote_path = f"{SERVER_FETCH_DIR}/{name}"
            local_path = clients_dir / name
            self._remote.get(remote_path, local_path)
            print(f"[remote] fetched {name}")