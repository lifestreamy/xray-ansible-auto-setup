"""Settings loading and CLI-override merging (PyYAML + pathlib, no regex)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

SETTINGS_FILE = "config/settings.yml"


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) to the repo root (the dir with deploy.yml)."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "deploy.yml").is_file():
            return candidate
    raise RuntimeError(f"repository root not found (no deploy.yml) from {current}")


def load_settings(repo_root: Path) -> dict[str, Any]:
    """Load config/settings.yml as a dict; errors are explicit."""
    settings_path = repo_root / SETTINGS_FILE
    if not settings_path.is_file():
        raise RuntimeError(f"settings file not found: {settings_path}")
    with settings_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise TypeError(f"settings file must contain a YAML mapping: {settings_path}")
    return data


def merge_overrides(settings: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Shallow merge; `overrides` win over `settings`."""
    merged = dict(settings)
    merged.update(overrides)
    return merged