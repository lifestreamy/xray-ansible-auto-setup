"""Tests for core/wsl.py: path translation and script assembly."""

from __future__ import annotations

import sys

import pytest

from xrayvpn.core.wsl import quote, to_wsl_path

windows_only = pytest.mark.skipif(
    sys.platform != "win32",
    reason="drive-letter translation is Windows-host semantics",
)


@windows_only
def test_to_wsl_path_drive_letter() -> None:
    assert to_wsl_path(r"C:\Users\Tim\proj") == "/mnt/c/Users/Tim/proj"


@windows_only
def test_to_wsl_path_lowercase_drive() -> None:
    assert to_wsl_path(r"z:\My_Xray\setup\xray-ansible") == "/mnt/z/My_Xray/setup/xray-ansible"


def test_to_wsl_path_without_drive() -> None:
    assert to_wsl_path(r"relative\path") == "relative/path"


def test_quote_wraps_spaces() -> None:
    assert quote("/mnt/z/a b/") == "'/mnt/z/a b/'"


def test_quote_plain() -> None:
    assert quote("deploy.yml") == "deploy.yml"