"""Tests for advanced feature engineering."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from b3quant.features.advanced_features import AdvancedFeatureEngineer


@pytest.fixture
def sample_options_with_greeks():
    """Create sample options DataFrame with Greeks."""
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    data = []

    for _i, trade_date in enumerate(dates):
        for strike in [95, 100, 105]:
            for opt_type in ["CALL", "PUT"]:
                data.append(
                    {
                        "ticker": f"PETR{opt_type[0]}{strike}",
                        "underlying": "PETR",
                        "trade_date": trade_date,
                        "instrument_type": opt_type,
                        "strike_price": float(strike),
                        "close_price": np.random.uniform(2, 8),
                        "close_price_underlying": 100 + np.random.randn() * 2,
                        "volume": np.random.randint(100, 1000),
                        "implied_volatility": 0.25 + np.random.randn() * 0.05,
                        "delta": 0.5 + np.random.randn() * 0.2,
                        "gamma": 0.02 + np.random.randn() * 0.005,
                        "vega": 30 + np.random.randn() * 5,
                    }
                )

    return pd.DataFrame(data)


@pytest.fixture
def sample_stocks_extended():
    """Create extended sample stocks DataFrame."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 2)

    return pd.DataFrame(
        {
            "underlying": ["PETR"] * 100,
            "trade_date": dates,
            "close_price": prices,
            "volume": np.random.randint(1000000, 5000000, size=100),
        }
    )


@pytest.fixture
def sample_benchmark():
    """Create sample benchmark DataFrame (e.g., IBOV)."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    np.random.seed(43)
    prices = 10000 + np.cumsum(np.random.randn(100) * 50)

    return pd.DataFrame(
        {
            "trade_date": dates,
            "close_price": prices,
        }
    )


class TestAdvancedFeatureEngineer:
    """Test AdvancedFeatureEngineer class."""

    def test_init_default(self):
        """Test initialization with default parameters."""
        fe = AdvancedFeatureEngineer()
        assert fe.lookback_windows == [10, 30, 60]
        assert fe.regime_windows == [20, 50, 100]

    def test_init_custom_windows(self):
        """Test initialization with custom windows."""
        fe = AdvancedFeatureEngineer(lookback_windows=[5, 20], regime_windows=[10, 30])
        assert fe.lookback_windows == [5, 20]
        assert fe.regime_windows == [10, 30]

    def test_add_greeks_exposure(
        self, sample_options_with_greeks, sample_stocks_extended
    ):
        """Test Greeks exposure features."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_greeks_exposure(
            sample_options_with_greeks, sample_stocks_extended
        )

        assert "total_gamma_exposure" in result.columns
        assert "total_vega_exposure" in result.columns
        assert "delta_weighted_volume" in result.columns
        assert "delta_hedged_value" in result.columns

        assert result["total_gamma_exposure"].notna().any()
        assert result["total_vega_exposure"].notna().any()

    def test_add_greeks_exposure_no_greeks(self):
        """Test Greeks exposure with DataFrame missing Greeks columns."""
        df = pd.DataFrame(
            {
                "underlying": ["PETR"],
                "trade_date": [date(2024, 1, 1)],
                "close_price": [5.0],
            }
        )

        fe = AdvancedFeatureEngineer()
        result = fe.add_greeks_exposure(df)

        assert len(result) == len(df)

    def test_add_volatility_of_volatility(self, sample_options_with_greeks):
        """Test volatility of volatility features."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_volatility_of_volatility(sample_options_with_greeks)

        assert any("vol_of_vol" in col for col in result.columns)
        assert any("iv_skewness" in col for col in result.columns)

    def test_add_bollinger_bands(self, sample_options_with_greeks):
        """Test Bollinger Bands features."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_bollinger_bands(sample_options_with_greeks)

        assert any("bb_width" in col for col in result.columns)
        assert any("bb_position" in col for col in result.columns)

        bb_position_cols = [col for col in result.columns if "bb_position" in col]
        if bb_position_cols:
            for col in bb_position_cols:
                valid_values = result[col].dropna()
                if len(valid_values) > 0:
                    assert valid_values.between(-0.5, 1.5).all()

    def test_add_rsi(self, sample_options_with_greeks):
        """Test RSI calculation."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_rsi(sample_options_with_greeks, period=14)

        assert "rsi_14d" in result.columns

        rsi_values = result["rsi_14d"].dropna()
        if len(rsi_values) > 0:
            assert rsi_values.between(0, 100).all()

    def test_add_rsi_custom_period(self, sample_options_with_greeks):
        """Test RSI with custom period."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_rsi(sample_options_with_greeks, period=20)

        assert "rsi_20d" in result.columns

    def test_add_regime_features(self, sample_options_with_greeks, sample_benchmark):
        """Test regime detection features."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_regime_features(sample_options_with_greeks, sample_benchmark)

        assert any("regime_volatility" in col for col in result.columns)
        assert any("regime_trend_strength" in col for col in result.columns)
        assert any("regime_autocorr" in col for col in result.columns)
        assert any("is_trending" in col for col in result.columns)
        assert any("is_ranging" in col for col in result.columns)
        assert any("is_volatile" in col for col in result.columns)

        trending_cols = [col for col in result.columns if "is_trending" in col]
        for col in trending_cols:
            assert result[col].isin([0, 1, np.nan]).all()

    def test_add_regime_features_no_benchmark(self, sample_options_with_greeks):
        """Test regime features without benchmark."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_regime_features(sample_options_with_greeks)

        assert any("regime_volatility" in col for col in result.columns)
        assert any("is_trending" in col for col in result.columns)

        assert not any("benchmark_corr" in col for col in result.columns)

    def test_add_all_advanced_features(
        self, sample_options_with_greeks, sample_stocks_extended, sample_benchmark
    ):
        """Test adding all advanced features at once."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_all_advanced_features(
            sample_options_with_greeks, sample_stocks_extended, sample_benchmark
        )

        assert "total_gamma_exposure" in result.columns
        assert any("vol_of_vol" in col for col in result.columns)
        assert any("bb_width" in col for col in result.columns)
        assert "rsi_14d" in result.columns
        assert any("regime_volatility" in col for col in result.columns)

    def test_add_all_advanced_features_minimal(self, sample_options_with_greeks):
        """Test adding features with minimal data."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_all_advanced_features(sample_options_with_greeks)

        assert len(result) == len(sample_options_with_greeks)

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame()
        fe = AdvancedFeatureEngineer()

        result = fe.add_greeks_exposure(df)
        assert len(result) == 0

        result = fe.add_volatility_of_volatility(df)
        assert len(result) == 0

    def test_bollinger_bands_custom_std(self, sample_options_with_greeks):
        """Test Bollinger Bands with custom standard deviation."""
        fe = AdvancedFeatureEngineer()
        result = fe.add_bollinger_bands(sample_options_with_greeks, num_std=3.0)

        assert any("bb_width" in col for col in result.columns)

    def test_insufficient_data(self):
        """Test with insufficient data for rolling calculations."""
        df = pd.DataFrame(
            {
                "underlying": ["PETR"],
                "trade_date": [date(2024, 1, 1)],
                "close_price_underlying": [100.0],
                "implied_volatility": [0.25],
            }
        )

        fe = AdvancedFeatureEngineer()
        result = fe.add_volatility_of_volatility(df)

        assert len(result) == len(df)
