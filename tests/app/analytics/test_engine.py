from __future__ import annotations

from datetime import date

import pyarrow as pa

from merlin.app.analytics.engine import AnalyticsEngine
from merlin.app.analytics.queries import (
    correlation_matrix,
    daily_returns,
    moving_average,
    symbol_summary,
)


def _sample_ohlcv() -> pa.Table:
    dates = [date(2025, 1, i) for i in range(1, 11)]
    return pa.table(
        {
            "symbol": pa.array(["AAPL"] * 10 + ["MSFT"] * 10, type=pa.string()),
            "market_date": pa.array(dates + dates, type=pa.date32()),
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
            "volume": pa.array(
                [1000000] * 20,
                type=pa.int64(),
            ),
        }
    )


class TestAnalyticsEngine:
    def test_register_and_query(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())

            result = engine.query("SELECT COUNT(*) AS cnt FROM ohlcv")
            assert result["cnt"][0] == 20

    def test_query_filter(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())

            result = engine.query("SELECT COUNT(*) AS cnt FROM ohlcv WHERE symbol = 'AAPL'")
            assert result["cnt"][0] == 10

    def test_context_manager(self) -> None:
        engine = AnalyticsEngine()
        engine.register_table("ohlcv", _sample_ohlcv())
        engine.close()


class TestAnalyticsQueries:
    def test_daily_returns(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = daily_returns(engine)

            assert "daily_return" in result.columns
            assert len(result) == 20
            # First row per symbol has null return
            aapl_returns = result.filter(result["symbol"] == "AAPL")
            assert aapl_returns["daily_return"][0] is None

    def test_moving_average(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = moving_average(engine, window=3)

            assert "ma_3" in result.columns
            assert len(result) == 20

    def test_symbol_summary(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = symbol_summary(engine)

            assert len(result) == 2
            assert "total_return" in result.columns
            symbols = result["symbol"].to_list()
            assert "AAPL" in symbols
            assert "MSFT" in symbols

    def test_correlation_matrix(self) -> None:
        with AnalyticsEngine() as engine:
            engine.register_table("ohlcv", _sample_ohlcv())
            result = correlation_matrix(engine)

            assert "correlation" in result.columns
            # Should have entries for AAPL-AAPL, AAPL-MSFT, MSFT-AAPL, MSFT-MSFT
            assert len(result) == 4
            # Self-correlation should be 1.0
            self_corr = result.filter(
                (result["symbol_a"] == "AAPL") & (result["symbol_b"] == "AAPL")
            )
            assert abs(self_corr["correlation"][0] - 1.0) < 0.01
