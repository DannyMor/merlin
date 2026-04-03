from merlin.app.market.models.asset import Asset, AssetType


class TestAsset:
    def test_create_etf(self) -> None:
        asset = Asset(symbol="SPY", name="SPDR S&P 500", asset_type=AssetType.ETF)
        assert asset.symbol == "SPY"
        assert asset.asset_type == AssetType.ETF
        assert asset.active is True

    def test_create_stock(self) -> None:
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            asset_type=AssetType.STOCK,
            exchange="NASDAQ",
        )
        assert asset.exchange == "NASDAQ"

    def test_asset_types(self) -> None:
        assert AssetType.ETF == "etf"
        assert AssetType.STOCK == "stock"
        assert AssetType.BOND == "bond"
