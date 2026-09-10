"""Settings loading and CLI-override merging (PyYAML + pathlib, no regex)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from xrayvpn.core.runtime_paths import require_repo_root

SETTINGS_FILE = "config/settings.yml"

find_repo_root = require_repo_root


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