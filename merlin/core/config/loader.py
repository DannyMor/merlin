from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

import yaml

from merlin.core.config.models import MerlinConfig

if TYPE_CHECKING:
    from pathlib import Path


def load_config(path: Path | None = None) -> MerlinConfig:
    """Load config from YAML file, then apply environment variable overrides.

    Environment variables follow the pattern MERLIN__SECTION__KEY (double underscore
    as separator). For example:
        MERLIN__DB__HOST=myhost
        MERLIN__WORKER__POLL_INTERVAL_SECONDS=10.0
    """
    raw: dict[str, object] = {}

    if path is not None and path.exists():
        with open(path) as f:
            loaded = yaml.safe_load(f)
        if isinstance(loaded, dict):
            raw = cast("dict[str, object]", loaded)

    _apply_env_overrides(raw)

    return MerlinConfig.model_validate(raw)


def _apply_env_overrides(raw: dict[str, object]) -> None:
    """Apply MERLIN__SECTION__KEY environment variables as overrides."""
    prefix = "MERLIN__"

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        parts = key[len(prefix) :].lower().split("__")

        match parts:
            case [section, field]:
                section_dict = raw.get(section)
                if not isinstance(section_dict, dict):
                    section_dict = {}
                    raw[section] = section_dict
                section_dict[field] = value
            case _:
                continue
