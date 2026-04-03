from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from merlin.app.analytics.engine import AnalyticsEngine


def daily_returns(engine: AnalyticsEngine, table_name: str = "ohlcv") -> pl.DataFrame:
    return engine.query(f"""
        SELECT
            symbol,
            market_date,
            close,
            (close - LAG(close) OVER (PARTITION BY symbol ORDER BY market_date))
                / LAG(close) OVER (PARTITION BY symbol ORDER BY market_date) AS daily_return
        FROM {table_name}
        ORDER BY symbol, market_date
    """)


def moving_average(
    engine: AnalyticsEngine,
    window: int = 20,
    table_name: str = "ohlcv",
) -> pl.DataFrame:
    return engine.query(f"""
        SELECT
            symbol,
            market_date,
            close,
            AVG(close) OVER (
                PARTITION BY symbol
                ORDER BY market_date
                ROWS BETWEEN {window - 1} PRECEDING AND CURRENT ROW
            ) AS ma_{window}
        FROM {table_name}
        ORDER BY symbol, market_date
    """)


def symbol_summary(engine: AnalyticsEngine, table_name: str = "ohlcv") -> pl.DataFrame:
    return engine.query(f"""
        SELECT
            symbol,
            COUNT(*) AS trading_days,
            MIN(market_date) AS first_date,
            MAX(market_date) AS last_date,
            MIN(low) AS period_low,
            MAX(high) AS period_high,
            FIRST(close ORDER BY market_date) AS first_close,
            LAST(close ORDER BY market_date) AS last_close,
            (LAST(close ORDER BY market_date) - FIRST(close ORDER BY market_date))
                / FIRST(close ORDER BY market_date) AS total_return
        FROM {table_name}
        GROUP BY symbol
        ORDER BY symbol
    """)


def correlation_matrix(engine: AnalyticsEngine, table_name: str = "ohlcv") -> pl.DataFrame:
    return engine.query(f"""
        WITH returns AS (
            SELECT
                symbol,
                market_date,
                (close - LAG(close) OVER (PARTITION BY symbol ORDER BY market_date))
                    / LAG(close) OVER (PARTITION BY symbol ORDER BY market_date) AS ret
            FROM {table_name}
        )
        SELECT
            a.symbol AS symbol_a,
            b.symbol AS symbol_b,
            CORR(a.ret, b.ret) AS correlation
        FROM returns a
        JOIN returns b ON a.market_date = b.market_date
        WHERE a.ret IS NOT NULL AND b.ret IS NOT NULL
        GROUP BY a.symbol, b.symbol
        ORDER BY a.symbol, b.symbol
    """)
