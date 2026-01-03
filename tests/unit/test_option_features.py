"""Tests for option feature engineering."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from b3quant.features.option_features import OptionFeatureEngineer


@pytest.fixture
def sample_options_df():
    """Create sample options DataFrame for testing."""
    return pd.DataFrame(
        {
            "ticker": ["PETRV100", "PETRW100", "PETRV105", "PETRW105"],
            "underlying": ["PETR", "PETR", "PETR", "PETR"],
            "trade_date": [date(2024, 1, 15)] * 4,
            "instrument_type": ["CALL", "PUT", "CALL", "PUT"],
            "strike_price": [100.0, 100.0, 105.0, 105.0],
            "close_price": [5.0, 3.0, 2.5, 5.5],
            "close_price_underlying": [102.0, 102.0, 102.0, 102.0],
            "maturity_date": [date(2024, 3, 15)] * 4,
            "time_to_maturity": [0.16] * 4,
            "days_to_maturity": [60] * 4,
            "volume": [1000.0, 800.0, 500.0, 600.0],
            "implied_volatility": [0.25, 0.30, 0.22, 0.28],
        }
    )


@pytest.fixture
def sample_stocks_df():
    """Create sample stocks DataFrame for testing."""
    dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(30) * 2)

    return pd.DataFrame(
        {
            "underlying": ["PETR"] * 30,
            "trade_date": dates,
            "close_price": prices,
            "volume": np.random.randint(1000000, 5000000, size=30),
        }
    )


class TestOptionFeatureEngineer:
    """Test OptionFeatureEngineer class."""

    def test_init_default(self):
        """Test initialization with default parameters."""
        fe = OptionFeatureEngineer()
        assert fe.lookback_windows == [10, 30, 60]

    def test_init_custom_windows(self):
        """Test initialization with custom lookback windows."""
        fe = OptionFeatureEngineer(lookback_windows=[5, 20])
        assert fe.lookback_windows == [5, 20]

    def test_add_moneyness_features(self, sample_options_df):
        """Test moneyness feature calculation."""
        fe = OptionFeatureEngineer()
        result = fe.add_moneyness_features(sample_options_df)

        assert "moneyness" in result.columns
        assert "log_moneyness" in result.columns
        assert "is_itm" in result.columns
        assert "is_atm" in result.columns
        assert "is_otm" in result.columns

        np.testing.assert_allclose(result["moneyness"].iloc[0], 102.0 / 100.0)
        np.testing.assert_allclose(
            result["log_moneyness"].iloc[0],
            np.log(102.0 / 100.0),
        )

        assert result["is_itm"].iloc[0] == 1
        assert result["is_otm"].iloc[1] == 1

    def test_add_time_features(self, sample_options_df):
        """Test time-related feature calculation."""
        fe = OptionFeatureEngineer()
        result = fe.add_time_features(sample_options_df)

        assert "day_of_week" in result.columns
        assert "day_of_month" in result.columns
        assert "month" in result.columns
        assert "quarter" in result.columns
        assert "is_month_end" in result.columns
        assert "is_quarter_end" in result.columns
        assert "sqrt_time" in result.columns
        assert "inv_sqrt_time" in result.columns
        assert "is_short_term" in result.columns
        assert "is_medium_term" in result.columns
        assert "is_long_term" in result.columns

        assert result["month"].iloc[0] == 1
        assert result["quarter"].iloc[0] == 1
        assert result["is_short_term"].iloc[0] == 1

    def test_add_volatility_features(self, sample_options_df):
        """Test volatility surface feature calculation."""
        df = sample_options_df.copy()

        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        expanded_data = []
        for i, trade_date in enumerate(dates):
            for _, row in sample_options_df.iterrows():
                new_row = row.copy()
                new_row["trade_date"] = trade_date
                new_row["implied_volatility"] = 0.25 + 0.05 * np.sin(i / 10)
                expanded_data.append(new_row)

        df = pd.DataFrame(expanded_data)

        fe = OptionFeatureEngineer()
        result = fe.add_volatility_features(df)

        assert any("iv_rank" in col for col in result.columns)
        assert any("iv_percentile" in col for col in result.columns)

    def test_add_market_features(self, sample_options_df, sample_stocks_df):
        """Test market microstructure feature calculation."""
        df = sample_options_df.copy()
        df["trade_date"] = pd.date_range(start="2024-01-15", periods=len(df), freq="D")

        fe = OptionFeatureEngineer()
        result = fe.add_market_features(df, sample_stocks_df)

        assert any("realized_vol" in col for col in result.columns)
        assert any("momentum" in col for col in result.columns)

    def test_calculate_iv_metrics(self, sample_options_df):
        """Test IV metrics calculation."""
        fe = OptionFeatureEngineer()
        result = fe.calculate_iv_metrics(sample_options_df)

        assert "iv_mean" in result.columns
        assert "iv_std" in result.columns
        assert "iv_min" in result.columns
        assert "iv_max" in result.columns
        assert "iv_median" in result.columns
        assert "iv_range" in result.columns
        assert "iv_cv" in result.columns

        assert len(result) == 1
        np.testing.assert_allclose(result["iv_mean"].iloc[0], 0.2625)

    def test_calculate_option_metrics(self, sample_options_df):
        """Test option-specific metrics calculation."""
        fe = OptionFeatureEngineer()
        result = fe.calculate_option_metrics(sample_options_df)

        assert "volume_pct" in result.columns
        assert "put_call_ratio" in result.columns

        total_volume = sample_options_df["volume"].sum()
        expected_pct = sample_options_df["volume"].iloc[0] / total_volume
        np.testing.assert_allclose(result["volume_pct"].iloc[0], expected_pct)

    def test_add_all_features(self, sample_options_df, sample_stocks_df):
        """Test adding all features at once."""
        fe = OptionFeatureEngineer()
        result = fe.add_all_features(sample_options_df, sample_stocks_df)

        assert "moneyness" in result.columns
        assert "log_moneyness" in result.columns
        assert "day_of_week" in result.columns
        assert "sqrt_time" in result.columns

    def test_add_all_features_no_stocks(self, sample_options_df):
        """Test adding features without stocks data."""
        fe = OptionFeatureEngineer()
        result = fe.add_all_features(sample_options_df)

        assert "moneyness" in result.columns
        assert "log_moneyness" in result.columns
        assert "day_of_week" in result.columns

    def test_calculate_iv_metrics_missing_column(self, sample_options_df):
        """Test IV metrics calculation with missing column."""
        fe = OptionFeatureEngineer()
        df = sample_options_df.drop(columns=["implied_volatility"])

        with pytest.raises(ValueError, match="implied_volatility"):
            fe.calculate_iv_metrics(df)

    def test_moneyness_edge_cases(self):
        """Test moneyness calculation with edge cases."""
        df = pd.DataFrame(
            {
                "underlying": ["TEST"],
                "instrument_type": ["CALL"],
                "strike_price": [100.0],
                "close_price_underlying": [100.0],
                "trade_date": [date(2024, 1, 1)],
            }
        )

        fe = OptionFeatureEngineer()
        result = fe.add_moneyness_features(df)

        assert result["moneyness"].iloc[0] == 1.0
        assert result["is_atm"].iloc[0] == 1

    def test_empty_dataframe(self):
        """Test feature engineering with empty DataFrame."""
        df = pd.DataFrame()
        fe = OptionFeatureEngineer()

        result = fe.add_moneyness_features(df)
        assert len(result) == 0
