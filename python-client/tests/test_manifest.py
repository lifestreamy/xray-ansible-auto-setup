"""Tests for core/manifest.py: allowlist tarball; inventory.yml NEVER included."""

from __future__ import annotations

import tarfile
from pathlib import Path

from xrayvpn.core.manifest import allowlist_entries, build_tarball


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    (repo / "deploy.yml").write_text("---\n", encoding="utf-8")
    role = repo / "roles" / "xray_vpn" / "tasks"
    role.mkdir(parents=True)
    (role / "main.yml").write_text("---\n", encoding="utf-8")
    (repo / "roles" / "xray_vpn" / "tasks" / "__pycache__").mkdir()
    (repo / "roles" / "xray_vpn" / "tasks" / "__pycache__" / "main.cpython.pyc").write_bytes(b"x")
    config = repo / "config"
    config.mkdir()
    (config / "settings.yml").write_text("a: 1\n", encoding="utf-8")
    (repo / "inventory.yml").write_text("secret\n", encoding="utf-8")
    (config / "inventory.yml").write_text("trap\n", encoding="utf-8")
    (repo / "hosts.retry").write_text("x\n", encoding="utf-8")
    (repo / "README.md").write_text("not in manifest\n", encoding="utf-8")
    return repo


def test_allowlist_entries(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    entries = allowlist_entries(repo)
    assert sorted(e.name for e in entries) == ["config", "deploy.yml", "roles"]


def test_tarball_contains_allowlist_only(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    dest = tmp_path / "bundle.tar.gz"
    build_tarball(repo, dest)
    with tarfile.open(dest) as archive:
        names = archive.getnames()
    assert "deploy.yml" in names
    assert "roles/xray_vpn/tasks/main.yml" in names
    assert "config/settings.yml" in names
    assert not any("inventory.yml" in name for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.endswith((".pyc", ".retry")) for name in names)
    assert "README.md" not in names
    assert not any("../" in name or name.startswith("/") for name in names)