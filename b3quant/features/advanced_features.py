"""Advanced feature engineering for options ML models."""

import numpy as np
import pandas as pd


class AdvancedFeatureEngineer:
    """Engineer advanced features for sophisticated ML models.

    Includes Greeks exposure, volatility of volatility, regime detection,
    and advanced technical indicators.
    """

    def __init__(
        self,
        lookback_windows: list[int] | None = None,
        regime_windows: list[int] | None = None,
    ):
        """
        Initialize advanced feature engineer.

        Args:
            lookback_windows: Periods for rolling calculations (default: [10, 30, 60])
            regime_windows: Windows for regime detection (default: [20, 50, 100])
        """
        self.lookback_windows = lookback_windows or [10, 30, 60]
        self.regime_windows = regime_windows or [20, 50, 100]

    def add_greeks_exposure(
        self, options_df: pd.DataFrame, stocks_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Add Greeks exposure features.

        Requires options with Greeks already calculated (delta, gamma, vega).
        """
        result = options_df.copy()

        if "delta" not in result.columns:
            return result

        for underlying in result["underlying"].unique():
            mask = result["underlying"] == underlying

            for date in result[mask]["trade_date"].unique():
                date_mask = mask & (result["trade_date"] == date)
                date_options = result[date_mask]

                if len(date_options) < 2:
                    continue

                if "gamma" in date_options.columns:
                    gamma_by_strike = date_options.groupby("strike_price")[
                        "gamma"
                    ].sum()
                    total_gamma = gamma_by_strike.sum()

                    result.loc[date_mask, "total_gamma_exposure"] = total_gamma
                    result.loc[date_mask, "max_gamma_strike"] = (
                        gamma_by_strike.idxmax() if len(gamma_by_strike) > 0 else np.nan
                    )

                if "vega" in date_options.columns:
                    total_vega = date_options["vega"].sum()
                    result.loc[date_mask, "total_vega_exposure"] = total_vega

                if "delta" in date_options.columns and "volume" in date_options.columns:
                    delta_weighted_volume = (
                        date_options["delta"].abs() * date_options["volume"]
                    ).sum()
                    result.loc[date_mask, "delta_weighted_volume"] = (
                        delta_weighted_volume
                    )

                if (
                    "delta" in date_options.columns
                    and "close_price_underlying" in date_options.columns
                    and stocks_df is not None
                ):
                    stock_data = stocks_df[
                        (stocks_df["underlying"] == underlying)
                        & (stocks_df["trade_date"] == date)
                    ]

                    if len(stock_data) > 0:
                        S = stock_data["close_price"].iloc[0]
                        delta_hedged_value = (
                            date_options["close_price"] - date_options["delta"] * S
                        ).mean()
                        result.loc[date_mask, "delta_hedged_value"] = delta_hedged_value

        return result

    def add_volatility_of_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility of volatility features.

        Measures how volatile the implied volatility itself is.
        """
        result = df.copy()

        if "implied_volatility" not in df.columns:
            return result

        for underlying in df["underlying"].unique():
            mask = df["underlying"] == underlying
            underlying_data = df[mask].sort_values("trade_date")

            if len(underlying_data) < 2:
                continue

            iv_series = underlying_data.groupby("trade_date")[
                "implied_volatility"
            ].mean()

            for window in self.lookback_windows:
                if len(iv_series) >= window:
                    iv_returns = iv_series.pct_change()
                    vol_of_vol = iv_returns.rolling(window).std()

                    result.loc[mask, f"vol_of_vol_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(vol_of_vol)

                    iv_skewness = iv_series.rolling(window).apply(
                        lambda x: pd.Series(x).skew() if len(x) > 2 else np.nan
                    )
                    result.loc[mask, f"iv_skewness_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(iv_skewness)

        return result

    def add_bollinger_bands(
        self, df: pd.DataFrame, num_std: float = 2.0
    ) -> pd.DataFrame:
        """Add Bollinger Bands features.

        Args:
            df: DataFrame with close_price_underlying column
            num_std: Number of standard deviations for bands (default: 2.0)
        """
        result = df.copy()

        if "close_price_underlying" not in df.columns:
            return result

        for underlying in df["underlying"].unique():
            mask = df["underlying"] == underlying
            underlying_data = df[mask].sort_values("trade_date")

            if len(underlying_data) < 2:
                continue

            prices = underlying_data.groupby("trade_date")[
                "close_price_underlying"
            ].first()

            for window in self.lookback_windows:
                if len(prices) >= window:
                    sma = prices.rolling(window).mean()
                    std = prices.rolling(window).std()

                    upper_band = sma + (std * num_std)
                    lower_band = sma - (std * num_std)

                    bb_width = (upper_band - lower_band) / sma
                    bb_position = (prices - lower_band) / (upper_band - lower_band)

                    result.loc[mask, f"bb_width_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(bb_width)
                    result.loc[mask, f"bb_position_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(bb_position)

        return result

    def add_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Relative Strength Index (RSI).

        Args:
            df: DataFrame with close_price_underlying column
            period: RSI period (default: 14)
        """
        result = df.copy()

        if "close_price_underlying" not in df.columns:
            return result

        for underlying in df["underlying"].unique():
            mask = df["underlying"] == underlying
            underlying_data = df[mask].sort_values("trade_date")

            if len(underlying_data) < period + 1:
                continue

            prices = underlying_data.groupby("trade_date")[
                "close_price_underlying"
            ].first()

            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / (loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))

            result.loc[mask, f"rsi_{period}d"] = underlying_data["trade_date"].map(rsi)

        return result

    def add_regime_features(  # noqa: C901
        self, df: pd.DataFrame, benchmark_df: pd.DataFrame | None = None
    ) -> pd.DataFrame:
        """Add market regime detection features.

        Detects trending, ranging, and volatile regimes.

        Args:
            df: Options DataFrame
            benchmark_df: Optional benchmark (e.g., IBOV) for correlation
        """
        result = df.copy()

        if "close_price_underlying" not in df.columns:
            return result

        for underlying in df["underlying"].unique():
            mask = df["underlying"] == underlying
            underlying_data = df[mask].sort_values("trade_date")

            if len(underlying_data) < 2:
                continue

            prices = underlying_data.groupby("trade_date")[
                "close_price_underlying"
            ].first()

            for window in self.regime_windows:
                if len(prices) >= window:
                    returns = prices.pct_change()

                    volatility = returns.rolling(window).std() * np.sqrt(252)
                    trend_strength = prices.rolling(window).apply(
                        lambda x: (
                            abs(x.iloc[-1] - x.iloc[0]) / x.std() if x.std() > 0 else 0
                        )
                    )

                    autocorr = returns.rolling(window).apply(
                        lambda x: x.autocorr() if len(x) > 1 else 0
                    )

                    result.loc[mask, f"regime_volatility_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(volatility)
                    result.loc[mask, f"regime_trend_strength_{window}d"] = (
                        underlying_data["trade_date"].map(trend_strength)
                    )
                    result.loc[mask, f"regime_autocorr_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(autocorr)

                    is_trending = (trend_strength > 1.5).astype(int)
                    is_ranging = ((trend_strength <= 1.5) & (volatility < 0.3)).astype(
                        int
                    )
                    is_volatile = (volatility > 0.5).astype(int)

                    result.loc[mask, f"is_trending_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(is_trending)
                    result.loc[mask, f"is_ranging_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(is_ranging)
                    result.loc[mask, f"is_volatile_{window}d"] = underlying_data[
                        "trade_date"
                    ].map(is_volatile)

            if benchmark_df is not None:
                benchmark_returns = (
                    benchmark_df.set_index("trade_date")["close_price"]
                    .pct_change()
                    .dropna()
                )
                stock_returns = prices.pct_change().dropna()

                common_dates = benchmark_returns.index.intersection(stock_returns.index)

                if len(common_dates) >= 30:
                    for window in self.regime_windows:
                        if len(common_dates) >= window:
                            rolling_corr = pd.Series(index=common_dates, dtype=float)

                            for date in common_dates:
                                window_dates = common_dates[common_dates <= date][
                                    -window:
                                ]
                                if len(window_dates) >= window:
                                    corr = stock_returns[window_dates].corr(
                                        benchmark_returns[window_dates]
                                    )
                                    rolling_corr[date] = corr

                            result.loc[mask, f"benchmark_corr_{window}d"] = (
                                underlying_data["trade_date"].map(rolling_corr)
                            )

        return result

    def add_all_advanced_features(
        self,
        options_df: pd.DataFrame,
        stocks_df: pd.DataFrame | None = None,
        benchmark_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Add all advanced features at once."""
        df = options_df.copy()

        df = self.add_greeks_exposure(df, stocks_df)
        df = self.add_volatility_of_volatility(df)
        df = self.add_bollinger_bands(df)
        df = self.add_rsi(df)
        df = self.add_regime_features(df, benchmark_df)

        return df
