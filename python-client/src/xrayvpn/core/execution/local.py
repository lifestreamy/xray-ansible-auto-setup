"""LocalExecutor — ansible runs on this machine against a remote VPS over SSH.

Windows: the existing WSL bridge is the transport (same venv requirements as
`scripts/test/local_test.py`); Linux/macOS: the control node runs natively.
The ansible TARGET is always the VPS — the old local-target execution was a
test-bench trick and now lives only in `scripts/test` + molecule.

Command builders are pure functions; the class resolves the control-node
environment (preflight), writes a 0600 ssh-target inventory, runs the
playbook, then pulls generated client configs with an `ansible.builtin.fetch`
playbook over the same SSH credentials.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from xrayvpn.core import wsl
from xrayvpn.core.execution.base import DeployRequest, extra_var_args

DEFAULT_WSL_VENV = "~/xray-venv"
COLLECTIONS_DIR = "xrayvpn-collections"
SERVER_FETCH_DIR = "/tmp/xrayvpn-fetch"
CONFIG_SOURCE = "/root/vpn-configs"
SSH_ARGS = "-o StrictHostKeyChecking=accept-new"

VENV_HINT = (
    "create it: python3 -m venv ~/xray-venv && ~/xray-venv/bin/pip install "
    "'ansible-core==2.21.3' (Debian/Ubuntu also need: sudo apt-get install "
    "python3-venv sshpass) — or use --execution remote instead"
)
SSHPASS_HINT = (
    "local execution with a password needs sshpass on the control node "
    "(`sudo apt-get install sshpass` in WSL / your package manager elsewhere) "
    "— or provide --pkey"
)

_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[\\/]")

FETCH_PLAYBOOK = """- name: Fetch client configs
  hosts: vpn
  gather_facts: false
  tasks:
    - name: Stage generated configs world-readable
      ansible.builtin.shell: >
        mkdir -p {stage_dir};
        cp {config_source}/*.json {config_source}/*.yaml {stage_dir}/ 2>/dev/null;
        chmod -R a+rX {stage_dir}
      become: true
      changed_when: false
      failed_when: false
    - name: Find staged configs
      ansible.builtin.find:
        paths: "{stage_dir}"
        patterns: ["*.json", "*.yaml"]
      register: staged
    - name: Copy configs to the control node
      ansible.builtin.fetch:
        src: "{{{{ item.path }}}}"
        dest: "{dest}/"
        flat: true
      loop: "{{{{ staged.files }}}}"
      loop_control:
        label: "{{{{ item.path }}}}"
"""


def build_ssh_inventory_vars(target: dict[str, str]) -> dict[str, str]:
    """Host vars for an ssh-target inventory; the host name stays `vpn`."""
    params = {
        "ansible_host": target["host"],
        "ansible_user": target["user"],
        "ansible_port": str(target.get("port", "22")),
    }
    if target.get("pkey"):
        params["ansible_ssh_private_key_file"] = target["pkey"]
    elif target.get("password"):
        params["ansible_ssh_pass"] = target["password"]
    return params


class LocalExecutor:
    def __init__(
        self,
        *,
        wsl_venv: str = DEFAULT_WSL_VENV,
        wsl_distro: str | None = None,
    ) -> None:
        self.wsl_venv = wsl_venv
        self.wsl_distro = wsl_distro
        self._wsl_home: str | None = None

    # --- control-node paths (pure) ---

    def venv_binary(self, wsl_home: str | None = None) -> str:
        """Path to the ansible-playbook binary the executor will invoke."""
        venv = self.wsl_venv
        if wsl_home and venv.startswith("~"):
            venv = wsl_home + venv[1:]
        return f"{venv}/bin/ansible-playbook"

    def galaxy_binary(self, wsl_home: str | None = None) -> str:
        return self.venv_binary(wsl_home=wsl_home).replace("ansible-playbook", "ansible-galaxy")

    def collections_path(self, wsl_home: str | None = None) -> str:
        base = wsl_home or str(Path.home())
        return f"{base}/{COLLECTIONS_DIR}"

    # --- command construction (pure, unit-testable) ---

    def deploy_argv(self, request: DeployRequest, inventory: Path) -> list[str]:
        parts = [self.venv_binary_for_run(), "deploy.yml", "-i", str(inventory)]
        if request.verbosity >= 4:
            parts.append("-vvvv")
        elif request.verbosity == 3:
            parts.append("-vvv")
        if request.debug:
            parts += ["-e", "xray_debug=true"]
        parts += extra_var_args(request.overrides)
        if request.dry_run:
            parts.append("--check")
        return parts

    def fetch_argv(self, inventory: Path, playbook: Path) -> list[str]:
        return [self.venv_binary_for_run(), "-i", str(inventory), str(playbook)]

    def fetch_playbook_text(self, clients_dir: Path) -> str:
        return FETCH_PLAYBOOK.format(
            stage_dir=SERVER_FETCH_DIR,
            config_source=CONFIG_SOURCE,
            dest=clients_dir.as_posix(),
        )

    def build_wsl_script(self, argv: list[str], repo_root: Path) -> str:
        home = self._wsl_home or "$HOME"
        translated = [
            wsl.to_wsl_path(part) if _WINDOWS_PATH.match(part) else part for part in argv
        ]
        quoted = " ".join(wsl.quote(part) for part in translated)
        colls = f"$HOME/{COLLECTIONS_DIR}"
        gal = self.galaxy_binary(wsl_home=home)
        return (
            f"cd {wsl.quote(wsl.to_wsl_path(repo_root))} && "
            f"[ -d {colls}/ansible_collections/community/general ] || "
            f"{wsl.quote(gal)} collection install community.general -p {colls} || exit 22; "
            f"ANSIBLE_FORCE_COLOR=1 "
            f"ANSIBLE_COLLECTIONS_PATH={colls} "
            f"ANSIBLE_SSH_ARGS={wsl.quote(SSH_ARGS)} {quoted}"
        )

    # --- executor surface ---

    def _native_binary(self) -> str | None:
        configured = Path(self.wsl_venv).expanduser() / "bin" / "ansible-playbook"
        if configured.is_file():
            return str(configured)
        return shutil.which("ansible-playbook")

    def _native_galaxy(self) -> str | None:
        configured = Path(self.wsl_venv).expanduser() / "bin" / "ansible-galaxy"
        if configured.is_file():
            return str(configured)
        return shutil.which("ansible-galaxy")

    def preflight(self, *, password_auth: bool) -> None:
        """Check the control-node environment; raise RuntimeError with a hint."""
        if wsl.is_windows():
            if not wsl.wsl_available():
                raise RuntimeError(
                    "local execution on Windows requires WSL; install WSL "
                    "(wsl --install) or use --execution remote"
                )
            self._wsl_home = wsl.wsl_home(self.wsl_distro)
            binary = self.venv_binary(wsl_home=self._wsl_home)
            if not wsl.path_exists(binary, distro=self.wsl_distro):
                raise RuntimeError(
                    f"ansible-playbook not found in WSL at {binary}; {VENV_HINT}"
                )
            if password_auth and not wsl.command_exists("sshpass", distro=self.wsl_distro):
                raise RuntimeError(SSHPASS_HINT)
            return
        if self._native_binary() is None:
            raise RuntimeError(
                f"ansible-playbook not found ({self.wsl_venv}/bin or PATH); {VENV_HINT}"
            )
        if password_auth and shutil.which("sshpass") is None:
            raise RuntimeError(SSHPASS_HINT)

    def venv_binary_for_run(self) -> str:
        """Binary path in the coordinate space of the runner (preflight first)."""
        if wsl.is_windows():
            return self.venv_binary(wsl_home=self._wsl_home)
        return self._native_binary() or self.venv_binary()

    def run(self, argv: list[str], request: DeployRequest) -> int:
        if not wsl.is_windows():
            colls = Path(self.collections_path())
            if not (colls / "ansible_collections" / "community" / "general").is_dir():
                galaxy = self._native_galaxy()
                if galaxy is None or subprocess.call(
                    [galaxy, "collection", "install", "community.general", "-p", str(colls)]
                ) != 0:
                    return 22
            env = dict(os.environ)
            env.setdefault("ANSIBLE_FORCE_COLOR", "1")
            env["ANSIBLE_COLLECTIONS_PATH"] = str(colls)
            env.setdefault("ANSIBLE_SSH_ARGS", SSH_ARGS)
            return subprocess.call(argv, cwd=str(request.repo_root), env=env)
        script = self.build_wsl_script(argv, request.repo_root)
        print(f"[local] wsl bash -lc {wsl.quote(script)}")
        return wsl.run_script(script, distro=self.wsl_distro)

    def deploy(self, request: DeployRequest, inventory: Path) -> int:
        return self.run(self.deploy_argv(request, inventory), request)

    def fetch_configs(self, request: DeployRequest, inventory: Path) -> None:
        clients = request.resolved_clients_dir()
        clients.mkdir(parents=True, exist_ok=True)
        playbook = request.repo_root / ".xrayvpn-fetch-playbook.yml"
        playbook.write_text(self.fetch_playbook_text(clients), encoding="utf-8")
        try:
            self.run(self.fetch_argv(inventory, playbook), request)
        finally:
            playbook.unlink(missing_ok=True)

    def cleanup(self, request: DeployRequest) -> None:
        """Nothing to clean on the target for local execution; run() removes the
        ad-hoc fetch playbook itself."""
