from datetime import date

from merlin.app.market.models.records import DividendRecord, OHLCVRecord, SplitRecord


class TestOHLCVRecord:
    def test_create(self) -> None:
        record = OHLCVRecord(
            symbol="AAPL",
            market_date=date(2025, 1, 15),
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=50000000,
        )
        assert record.symbol == "AAPL"
        assert record.adjusted_close is None

    def test_with_adjusted_close(self) -> None:
        record = OHLCVRecord(
            symbol="AAPL",
            market_date=date(2025, 1, 15),
            open=150.0,
            high=155.0,
            low=149.0,
            close=153.0,
            volume=50000000,
            adjusted_close=152.5,
        )
        assert record.adjusted_close == 152.5


class TestDividendRecord:
    def test_create(self) -> None:
        record = DividendRecord(
            symbol="AAPL",
            market_date=date(2025, 1, 15),
            amount=0.25,
        )
        assert record.amount == 0.25


class TestSplitRecord:
    def test_create(self) -> None:
        record = SplitRecord(
            symbol="AAPL",
            market_date=date(2025, 1, 15),
            ratio=4.0,
        )
        assert record.ratio == 4.0
