"""Load YAML config files from ./config."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@cache
def load(name: str) -> dict[str, Any]:
    """Load config/<name>.yaml (cached)."""
    with (CONFIG_DIR / f"{name}.yaml").open() as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return data
