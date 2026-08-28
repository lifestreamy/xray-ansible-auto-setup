"""Upload manifest — explicit allowlist (ADR-008).

Only these repository entries may be uploaded to a target server:
`deploy.yml`, `roles/`, `config/`. `inventory.yml` is NEVER uploaded, wherever
it appears; junk (__pycache__, *.retry, *.pyc) is pruned. Files are added
under repo-relative arcnames so the archive extracts as a project root.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

ALLOWED_TOP_LEVEL = ("deploy.yml", "roles", "config")

NEVER_UPLOAD_NAMES = {"inventory.yml"}
SKIP_DIR_NAMES = {"__pycache__", ".git"}
SKIP_FILE_SUFFIXES = {".pyc", ".retry"}


def allowlist_entries(repo_root: Path) -> list[Path]:
    """Top-level allowlisted entries that exist in the repo."""
    entries: list[Path] = []
    for name in ALLOWED_TOP_LEVEL:
        candidate = repo_root / name
        if candidate.exists():
            entries.append(candidate)
    return entries


def _iter_files(entry: Path):
    """Yield files under `entry`, skipping junk dirs/files (recursive walk)."""
    if entry.is_dir():
        for child in sorted(entry.iterdir()):
            if child.is_dir() and child.name in SKIP_DIR_NAMES:
                continue
            yield from _iter_files(child)
    elif entry.is_file():
        yield entry


def _should_skip(rel: Path) -> bool:
    if rel.name in NEVER_UPLOAD_NAMES:
        return True
    return rel.suffix in SKIP_FILE_SUFFIXES


def build_tarball(repo_root: Path, dest: Path) -> Path:
    """Build `dest` (tar.gz) with only allowlisted, never-upload-safe files."""
    with tarfile.open(dest, "w:gz") as archive:
        for entry in allowlist_entries(repo_root):
            for member in _iter_files(entry):
                rel = member.relative_to(repo_root)
                if _should_skip(rel):
                    continue
                archive.add(member, arcname=rel.as_posix())
    return dest