"""LocalExecutor — playbook runs on the current machine.

- Linux: direct subprocess call of venv ansible-playbook.
- Windows: WSL bridge (detect `wsl --status`, /mnt path translation, bash -lc).
Client configs are copied from /root/vpn-configs afterwards (same contract as
the shell-script fetch step).
"""

from __future__ import annotations

import subprocess

from xrayvpn.core import wsl
from xrayvpn.core.execution.base import DeployRequest, extra_var_args
from xrayvpn.core.inventory import INVENTORY_FILE

DEFAULT_WSL_VENV = "~/xray-venv"


class LocalExecutor:
    def __init__(
        self,
        *,
        wsl_venv: str = DEFAULT_WSL_VENV,
        wsl_distro: str | None = None,
    ) -> None:
        self.wsl_venv = wsl_venv
        self.wsl_distro = wsl_distro

    # --- command construction (pure, unit-testable) ---

    def _ansible_playbook(self, wsl_home: str | None = None) -> str:
        venv = self.wsl_venv
        if wsl_home and venv.startswith("~"):
            venv = wsl_home + venv[1:]
        return f"{venv}/bin/ansible-playbook"

    def _inventory(self, request: DeployRequest) -> str:
        return str(
            request.inventory_path or (request.repo_root / INVENTORY_FILE)
        )

    def build_command(self, request: DeployRequest) -> list[str]:
        cmd = [self._ansible_playbook(), "deploy.yml", "-i", self._inventory(request)]
        if request.verbosity >= 4:
            cmd.append("-vvvv")
        elif request.verbosity == 3:
            cmd.append("-vvv")
        if request.debug:
            cmd += ["-e", "xray_debug=true"]
        cmd += extra_var_args(request.overrides)
        if request.dry_run:
            cmd.append("--check")
        return cmd

    def build_wsl_script(self, request: DeployRequest, wsl_home: str) -> str:
        repo = wsl.to_wsl_path(request.repo_root)
        cmd = [
            self._ansible_playbook(wsl_home=wsl_home),
            "deploy.yml",
            "-i",
            wsl.to_wsl_path(self._inventory(request)),
        ]
        if request.verbosity >= 4:
            cmd.append("-vvvv")
        elif request.verbosity == 3:
            cmd.append("-vvv")
        if request.debug:
            cmd += ["-e", "xray_debug=true"]
        cmd += extra_var_args(request.overrides)
        if request.dry_run:
            cmd.append("--check")
        quoted = " ".join(wsl.quote(part) for part in cmd)
        return f"cd {wsl.quote(repo)} && ANSIBLE_FORCE_COLOR=1 {quoted}"

    # --- executor surface ---

    def deploy(self, request: DeployRequest) -> int:
        if not wsl.is_windows():
            cmd = self.build_command(request)
            print(f"[local] {' '.join(cmd)}")
            return subprocess.call(cmd, cwd=request.repo_root)

        if not wsl.wsl_available():
            raise RuntimeError(
                "local execution on Windows requires WSL; "
                "install WSL (wsl --install) or use --execution remote"
            )
        home = wsl.wsl_home(self.wsl_distro)
        script = self.build_wsl_script(request, home)
        print(f"[local] wsl bash -lc {wsl.quote(script)}")
        return wsl.run_script(script, distro=self.wsl_distro)

    def fetch_configs(self, request: DeployRequest) -> None:
        """Copy generated client configs from /root/vpn-configs into clients_dir."""
        clients = request.resolved_clients_dir()
        clients.mkdir(parents=True, exist_ok=True)
        source = "/root/vpn-configs"
        wsl_home_path = None
        if wsl.is_windows():
            wsl_home_path = wsl.to_wsl_path(clients)
        # Glob must expand inside sudo (the WSL user cannot read /root/vpn-configs).
        if wsl_home_path is not None:
            step = (
                f"sudo -n bash -c 'mkdir -p {wsl_home_path} && "
                f"cp {source}/*.json {source}/*.yaml {wsl_home_path}/ 2>/dev/null || true'"
            )
            print(f"[local] wsl bash -lc {wsl.quote(step)}")
            wsl.run_script(step, distro=self.wsl_distro)
        else:
            step = (
                f"sudo -n bash -c 'mkdir -p {wsl.quote(str(clients))} && "
                f"cp {source}/*.json {source}/*.yaml "
                f"{wsl.quote(str(clients))}/ 2>/dev/null || true'"
            )
            subprocess.call(["bash", "-lc", step])

    def cleanup(self, request: DeployRequest) -> None:
        """Nothing to clean for local execution."""