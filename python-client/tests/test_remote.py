"""Tests for core/execution/remote.py: bootstrap/cleanup commands, orchestration."""

from __future__ import annotations

from pathlib import Path

from xrayvpn.core.execution.base import DeployRequest
from xrayvpn.core.execution.remote import (
    ANSIBLE_CORE_PIN,
    SERVER_COLLECTIONS,
    SERVER_STAGING,
    SERVER_VENV,
    RemoteExecutor,
    bootstrap_commands,
    cleanup_commands,
    fetch_targets,
    playbook_command,
)
from xrayvpn.core.transport.remote import CommandResult


def test_bootstrap_commands_content() -> None:
    commands = bootstrap_commands()
    assert "python3 -V" in commands
    assert any("python3 -m venv" in c and SERVER_VENV in c for c in commands)
    # bare Debian/Ubuntu lack python3-venv → the venv line must carry the apt fallback
    assert any("apt-get install -y python3-venv" in c for c in commands)
    assert any(f"ansible-core=={ANSIBLE_CORE_PIN}" in c for c in commands)
    assert any("community.general" in c and SERVER_COLLECTIONS in c for c in commands)
    assert any(c.startswith(f"mkdir -p {SERVER_STAGING}") for c in commands)


def test_playbook_command_build() -> None:
    request = DeployRequest(repo_root=Path("."), overrides={}, verbosity=3, dry_run=True)
    command = playbook_command(request, {"warp_enabled": False, "xray_runtime": "native"})
    assert f"ANSIBLE_COLLECTIONS_PATH={SERVER_COLLECTIONS}" in command
    assert f"{SERVER_VENV}/bin/ansible-playbook" in command
    assert "-i inventory.yml" in command
    assert "deploy.yml" in command
    assert "-vvv" in command
    assert "'{\"warp_enabled\": false, \"xray_runtime\": \"native\"}'" in command
    assert "--check" in command


def test_cleanup_commands_modes() -> None:
    assert cleanup_commands("cleanup") == [f"rm -rf {SERVER_STAGING}"]
    assert cleanup_commands("full-cleanup") == [f"rm -rf {SERVER_STAGING} {SERVER_VENV}"]
    assert cleanup_commands("no-cleanup") == []


def test_fetch_targets_filters() -> None:
    listing = "clash.yaml\namnezia.json\nnotes.txt\nsubdir\n"
    assert fetch_targets(listing) == ["clash.yaml", "amnezia.json"]


class FakeRemote:
    """Recorded-run Remote stub: all commands succeed."""

    def __init__(self, listing: str = "clash.yaml\namnezia.json\n") -> None:
        self.commands: list[str] = []
        self.puts: list[tuple[str, str]] = []
        self.gets: list[tuple[str, str]] = []
        self.listing = listing

    def run(self, command, *, sudo=False, warn=True, env=None) -> CommandResult:
        self.commands.append(command)
        stdout = self.listing if "ls " in command else ""
        return CommandResult(return_code=0, stdout=stdout)

    def put(self, local, remote) -> None:
        self.puts.append((str(local), remote))

    def get(self, remote, local) -> None:
        self.gets.append((remote, str(local)))
        Path(local).write_text(f"# fake {Path(remote).name}\n", encoding="utf-8")

    def close(self) -> None:
        pass


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "deploy.yml").write_text("---\n", encoding="utf-8")
    (repo / "config").mkdir()
    (repo / "config" / "settings.yml").write_text("a: 1\n", encoding="utf-8")
    return repo


def test_deploy_orchestration(tmp_path: Path) -> None:
    remote = FakeRemote()
    executor = RemoteExecutor(remote, cleanup="cleanup")
    repo = _repo(tmp_path)
    request = DeployRequest(
        repo_root=repo,
        clients_dir=tmp_path / "clients",
        overrides={"warp_enabled": False},
    )
    rc = executor.deploy(request, extra_vars={"warp_enabled": False})

    assert rc == 0
    # bootstrap ran
    joined = "\n".join(remote.commands)
    assert f"ansible-core=={ANSIBLE_CORE_PIN}" in joined
    assert "pip install" in joined
    # extract + inventory + playbook + cleanup
    assert "tar -xzf" in joined
    assert "chmod 0600" in joined
    assert "ansible-playbook" in joined
    assert f"rm -rf {SERVER_STAGING}" in joined
    assert not any("SERVER_VENV" in c and "rm -rf" in c for c in remote.commands)
    # uploads: bundle + server inventory
    assert len(remote.puts) == 2
    assert remote.puts[0][1].endswith("bundle.tar.gz")
    assert remote.puts[1][1].endswith("inventory.yml")
    # fetched client configs
    assert len(remote.gets) == 2
    assert (tmp_path / "clients" / "clash.yaml").exists()


def test_deploy_playbook_failure_stops_flow(tmp_path: Path) -> None:
    class FailingRemote(FakeRemote):
        def run(self, command, *, sudo=False, warn=True, env=None) -> CommandResult:
            self.commands.append(command)
            if "ansible-playbook" in command:
                return CommandResult(return_code=4, stderr="boom")
            return CommandResult(return_code=0)

    remote = FailingRemote()
    executor = RemoteExecutor(remote, cleanup="cleanup")
    request = DeployRequest(repo_root=_repo(tmp_path), overrides={})
    rc = executor.deploy(request, extra_vars={})
    assert rc == 4
    assert not any("rm -rf" in c for c in remote.commands)