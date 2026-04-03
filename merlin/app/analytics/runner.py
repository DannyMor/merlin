from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import polars as pl

    from merlin.app.analytics.engine import AnalyticsEngine
    from merlin.app.analytics.models import ProcedureDef


class ProcedureRunner:
    def __init__(self, engines: dict[str, AnalyticsEngine]) -> None:
        self._engines = engines

    def run(self, procedure: ProcedureDef, params: dict[str, Any] | None = None) -> pl.DataFrame:
        engine = self._engines.get(procedure.engine)
        if engine is None:
            msg = f"No engine registered for type: {procedure.engine}"
            raise ValueError(msg)

        resolved = _resolve_params(procedure, params or {})
        sql = procedure.sql.format(**resolved)
        return engine.query(sql)


def _resolve_params(procedure: ProcedureDef, params: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for name, param_def in procedure.input.items():
        value = params.get(name, param_def.default)
        if value is None:
            msg = f"Missing required parameter: {name}"
            raise ValueError(msg)
        resolved[name] = value

    # Derived parameters for common patterns
    if "window" in resolved:
        resolved["window_minus_1"] = int(resolved["window"]) - 1

    return resolved
