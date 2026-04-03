from __future__ import annotations

from datetime import date
from pathlib import Path

import pyarrow as pa

from merlin.app.analytics.engine import DuckDBEngine
from merlin.app.analytics.loader import load_procedures_by_name
from merlin.app.analytics.models import ParamDef, ProcedureDef
from merlin.app.analytics.runner import ProcedureRunner


def _sample_ohlcv() -> pa.Table:
    dates = [date(2025, 1, i) for i in range(1, 11)]
    return pa.table(
        {
            "symbol": pa.array(
                [*["AAPL"] * 10, *["MSFT"] * 10],
                type=pa.string(),
            ),
            "market_date": pa.array([*dates, *dates], type=pa.date32()),
            "open": pa.array(
                [
                    *[150.0, 151.0, 152.0, 151.0, 153.0, 154.0, 155.0, 153.0, 156.0, 157.0],
                    *[300.0, 301.0, 302.0, 301.0, 303.0, 304.0, 305.0, 303.0, 306.0, 307.0],
                ],
                type=pa.float64(),
            ),
            "high": pa.array(
                [
                    *[155.0, 156.0, 157.0, 156.0, 158.0, 159.0, 160.0, 158.0, 161.0, 162.0],
                    *[305.0, 306.0, 307.0, 306.0, 308.0, 309.0, 310.0, 308.0, 311.0, 312.0],
                ],
                type=pa.float64(),
            ),
            "low": pa.array(
                [
                    *[148.0, 149.0, 150.0, 149.0, 151.0, 152.0, 153.0, 151.0, 154.0, 155.0],
                    *[298.0, 299.0, 300.0, 299.0, 301.0, 302.0, 303.0, 301.0, 304.0, 305.0],
                ],
                type=pa.float64(),
            ),
            "close": pa.array(
                [
                    *[152.0, 153.0, 154.0, 152.0, 155.0, 156.0, 157.0, 155.0, 158.0, 159.0],
                    *[302.0, 303.0, 304.0, 302.0, 305.0, 306.0, 307.0, 305.0, 308.0, 309.0],
                ],
                type=pa.float64(),
            ),
            "volume": pa.array([1000000] * 20, type=pa.int64()),
        }
    )


class TestDuckDBEngine:
    def test_register_and_query(self) -> None:
        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = engine.query("SELECT COUNT(*) AS cnt FROM ohlcv")
            assert result["cnt"][0] == 20

    def test_query_filter(self) -> None:
        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = engine.query("SELECT COUNT(*) AS cnt FROM ohlcv WHERE symbol = 'AAPL'")
            assert result["cnt"][0] == 10

    def test_context_manager(self) -> None:
        engine = DuckDBEngine()
        engine.register_table("ohlcv", _sample_ohlcv())
        engine.close()


class TestProcedureRunner:
    def test_run_inline_procedure(self) -> None:
        procedure = ProcedureDef(
            name="count_rows",
            engine="duckdb",
            input={"table_name": ParamDef(type="str", default="ohlcv")},
            output_schema={"cnt": "int"},
            sql="SELECT COUNT(*) AS cnt FROM {table_name}",
        )

        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedure)
            assert result["cnt"][0] == 20

    def test_run_with_param_override(self) -> None:
        procedure = ProcedureDef(
            name="count_rows",
            engine="duckdb",
            input={"table_name": ParamDef(type="str", default="ohlcv")},
            output_schema={"cnt": "int"},
            sql="SELECT COUNT(*) AS cnt FROM {table_name}",
        )

        with DuckDBEngine() as engine:
            engine.register_table("data", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedure, {"table_name": "data"})
            assert result["cnt"][0] == 20

    def test_run_missing_engine_raises(self) -> None:
        procedure = ProcedureDef(
            name="test",
            engine="nonexistent",
            sql="SELECT 1",
        )
        runner = ProcedureRunner({})
        try:
            runner.run(procedure)
            assert False, "Expected ValueError"  # noqa: B011
        except ValueError as e:
            assert "nonexistent" in str(e)


class TestProcedureFromYAML:
    def test_load_and_run_daily_returns(self) -> None:
        procedures = load_procedures_by_name(Path("config/procedures.yaml"))
        assert "daily_returns" in procedures

        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedures["daily_returns"])

            assert "daily_return" in result.columns
            assert len(result) == 20

    def test_load_and_run_moving_average(self) -> None:
        procedures = load_procedures_by_name(Path("config/procedures.yaml"))

        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedures["moving_average"], {"window": 3})

            assert "moving_avg" in result.columns
            assert len(result) == 20

    def test_load_and_run_symbol_summary(self) -> None:
        procedures = load_procedures_by_name(Path("config/procedures.yaml"))

        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedures["symbol_summary"])

            assert len(result) == 2
            assert "total_return" in result.columns

    def test_load_and_run_correlation_matrix(self) -> None:
        procedures = load_procedures_by_name(Path("config/procedures.yaml"))

        with DuckDBEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            runner = ProcedureRunner({"duckdb": engine})
            result = runner.run(procedures["correlation_matrix"])

            assert "correlation" in result.columns
            assert len(result) == 4
            self_corr = result.filter(
                (result["symbol_a"] == "AAPL") & (result["symbol_b"] == "AAPL")
            )
            assert abs(self_corr["correlation"][0] - 1.0) < 0.01
