from __future__ import annotations

from pathlib import Path

import yaml

from merlin.app.analytics.models import ProcedureDef


def load_procedures(path: Path | None = None) -> list[ProcedureDef]:
    if path is None:
        path = Path("config/procedures.yaml")

    with open(path) as f:
        data = yaml.safe_load(f)

    raw_procedures: list[dict[str, object]] = data.get("procedures", [])
    return [ProcedureDef.model_validate(p) for p in raw_procedures]


def load_procedures_by_name(path: Path | None = None) -> dict[str, ProcedureDef]:
    procedures = load_procedures(path)
    return {p.name: p for p in procedures}
