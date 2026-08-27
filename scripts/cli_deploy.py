#!/usr/bin/env python3
"""scripts/cli_deploy.py — MVP CLI wrapper around ansible-playbook deploy.yml.

Translates a small set of user-friendly flags into an inventory override
file and invokes the project's deploy playbook. Other variables continue
to come from config/settings.yml (loaded by deploy.yml via vars_files).

Usage:
    python3 scripts/cli_deploy.py --runtime native
    python3 scripts/cli_deploy.py --runtime docker --xray-port 8443
    python3 scripts/cli_deploy.py --num-clients 5 --camouflage-domain www.microsoft.com
    python3 scripts/cli_deploy.py --no-warp --rotate
    python3 scripts/cli_deploy.py --inventory my-vps --dry-run

Notes:
- This is an MVP. It does not aim to
  cover every variable; everything not exposed as a flag stays at the
  config/settings.yml default.
- The generated inventory file is written next to inventory.yml.example
  and is gitignored (inventory.yml is on the ignore list).
- --dry-run passes --check to ansible-playbook (no changes applied).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SUPPORTED_RUNTIMES = ("native", "docker", "podman")


def build_inventory(vars: dict[str, object]) -> str:
    """Render a one-host inventory YAML suitable for -i.

    The host is named `vpn` and uses ansible_connection=local so the
    MVP works on a fresh VPS without first bootstrapping SSH keys.
    Replace with a real ansible_host when you wire this to remote VPS.
    """
    import yaml

    body = {
        "all": {
            "hosts": {
                "vpn": {
                    "ansible_connection": "local",
                    "ansible_python_interpreter": sys.executable,
                }
            },
            "vars": vars,
        }
    }
    return yaml.safe_dump(body, sort_keys=False, allow_unicode=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--runtime",
        choices=SUPPORTED_RUNTIMES,
        default=None,
        help="xray_runtime selector (overrides config/settings.yml)",
    )
    parser.add_argument(
        "--xray-port",
        type=int,
        default=None,
        help="VLESS inbound TCP port (overrides xray_port)",
    )
    parser.add_argument(
        "--num-clients",
        type=int,
        default=None,
        help="Number of client configs to generate (overrides num_clients)",
    )
    parser.add_argument(
        "--camouflage-domain",
        default=None,
        help="REALITY camouflage/SNI domain (overrides reality_camouflage_domain)",
    )
    parser.add_argument(
        "--warp",
        dest="warp",
        action="store_true",
        default=None,
        help="Enable Cloudflare WARP outbound (sets warp_enabled=true)",
    )
    parser.add_argument(
        "--no-warp",
        dest="warp",
        action="store_false",
        help="Disable Cloudflare WARP outbound (sets warp_enabled=false)",
    )
    parser.add_argument(
        "--rotate",
        dest="rotate",
        action="store_true",
        default=None,
        help="Force REALITY key + UUID regeneration (sets xray_reality_rotate=true)",
    )
    parser.add_argument(
        "--no-rotate",
        dest="rotate",
        action="store_false",
        help="Do not force rotation (sets xray_reality_rotate=false)",
    )
    parser.add_argument(
        "--inventory",
        default=None,
        help="Path to a real inventory file with ansible_host (skips the "
             "generated localhost inventory).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --check to ansible-playbook; do not apply changes",
    )
    args = parser.parse_args()

    overrides: dict[str, object] = {}
    if args.runtime is not None:
        overrides["xray_runtime"] = args.runtime
    if args.xray_port is not None:
        overrides["xray_port"] = args.xray_port
    if args.num_clients is not None:
        overrides["num_clients"] = args.num_clients
    if args.camouflage_domain is not None:
        overrides["reality_camouflage_domain"] = args.camouflage_domain
    if args.warp is not None:
        overrides["warp_enabled"] = args.warp
    if args.rotate is not None:
        overrides["xray_reality_rotate"] = args.rotate

    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    if args.inventory is not None:
        inv_path = Path(args.inventory).expanduser().resolve()
        if not inv_path.exists():
            print(
                f"[cli-deploy] inventory file not found: {inv_path}",
                file=sys.stderr,
            )
            return 2
    else:
        inv_yaml = build_inventory(overrides)
        # Persist next to inventory.yml.example for visibility; the file
        # is gitignored (inventory.yml is on the ignore list).
        inv_path = repo_root / "inventory.yml"
        inv_path.write_text(inv_yaml, encoding="utf-8")
        print(f"[cli-deploy] generated {inv_path} with overrides: {overrides or '{}'}")

    cmd = [
        sys.executable,
        "-m",
        "ansible.cli.playbook",
        "deploy.yml",
        "-i",
        str(inv_path),
    ]
    if args.dry_run:
        cmd.append("--check")

    print(f"[cli-deploy] {' '.join(cmd)}")
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
