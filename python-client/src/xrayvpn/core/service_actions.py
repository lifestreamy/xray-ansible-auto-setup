"""Whitelisted remote commands for `xrayvpn service` (exact strings, no interpolation
of operator input beyond integer ports). This module never talks to the network."""

from __future__ import annotations

XRAY_UNITS = ("xray", "xray-obs-snapshot", "xray-watchdog")


def journal_filter() -> str:
    # repeated -u is journald OR of a single field; mixing -u and -t would AND.
    return " ".join(f"-u {unit}" for unit in XRAY_UNITS)


def status_commands(xray_port: int = 443, probe_port: int = 10820, minutes: int = 30) -> list[str]:
    port = int(xray_port)  # ports are ints from config, never free-form text
    probe = int(probe_port)
    mins = int(minutes)
    return [
        "systemctl is-active xray",
        "systemctl show xray -p NRestarts -p ActiveEnterTimestamp -p SubState",
        f"sudo -n journalctl -u xray --since '-{mins}m' -o cat | grep -Ec 'wireguard|outbound' || true",
        f"sudo -n journalctl {journal_filter()} --since '-{mins}m' -o short-iso --no-pager | tail -n 60",
        f"sudo -n ss -tulpn '( sport = :{port} or sport = :{probe} or sport = :22 )'",
        "free -m",
    ]


def restart_commands() -> list[str]:
    return [
        "sudo -n systemctl reset-failed xray",
        "sudo -n systemctl restart xray",
        "systemctl is-active xray",
    ]


def logs_journal_command(since: str) -> str:
    # `since` must match ^[0-9]+[mhd]$ (CLI normalizes before calling); never free text reaches the shell.
    # The journal is small by construction (capped in the role); stream it over SSH, no server-side file.
    return f"sudo -n journalctl {journal_filter()} --since \"-{since}\" -o short-iso --no-pager"


def reboot_command() -> str:
    return "sudo -n systemctl reboot"
