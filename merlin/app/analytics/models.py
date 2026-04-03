from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParamDef(BaseModel):
    type: str
    default: Any = None


class ProcedureDef(BaseModel):
    name: str
    description: str = ""
    input: dict[str, ParamDef] = Field(default_factory=dict)
    output_schema: dict[str, str] = Field(default_factory=dict)
    engine: str
    sql: str
