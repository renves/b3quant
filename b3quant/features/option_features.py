"""Advanced feature engineering for options data."""


import numpy as np
import pandas as pd


class OptionFeatureEngineer:
    """Engineer advanced features for options ML models.

    Implements state-of-the-art feature engineering for options pricing
    and trading models, including volatility surface features, market
    microstructure, and time series indicators.
    """

    def __init__(self, lookback_windows: list[int] | None = None):
        """
        Initialize feature engineer.

        Args:
            lookback_windows: Periods for rolling calculations (default: [10, 30, 60])
        """
        self.lookback_windows = lookback_windows or [10, 30, 60]

    def add_all_features(
        self,
        options_df: pd.DataFrame,
        stocks_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Add all feature categories to options DataFrame."""
        df = options_df.copy()

        df = self.add_moneyness_features(df)
        df = self.add_time_features(df)
        df = self.add_volatility_features(df)

        if stocks_df is not None:
            df = self.add_market_features(df, stocks_df)

        return df

    def add_moneyness_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moneyness-related features."""
        result = df.copy()

        if "close_price_underlying" in df.columns and "strike_price" in df.columns:
            S = df["close_price_underlying"]
            K = df["strike_price"]

            result["moneyness"] = S / K
            result["log_moneyness"] = np.log(S / K)

            result["is_itm"] = (
                ((df["instrument_type"] == "CALL") & (S > K))
                | ((df["instrument_type"] == "PUT") & (S < K))
            ).astype(int)

            result["is_atm"] = (
                (result["moneyness"] >= 0.95) & (result["moneyness"] <= 1.05)
            ).astype(int)

            result["is_otm"] = (
                ((df["instrument_type"] == "CALL") & (S <= K))
                | ((df["instrument_type"] == "PUT") & (S >= K))
            ).astype(int)

        return result

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-related features."""
        result = df.copy()

        if "trade_date" in df.columns:
            trade_date = pd.to_datetime(df["trade_date"])

            result["day_of_week"] = trade_date.dt.dayofweek
            result["day_of_month"] = trade_date.dt.day
            result["month"] = trade_date.dt.month
            result["quarter"] = trade_date.dt.quarter

            result["is_month_end"] = (trade_date.dt.is_month_end).astype(int)
            result["is_quarter_end"] = (trade_date.dt.is_quarter_end).astype(int)

        if "time_to_maturity" in df.columns:
            T = df["time_to_maturity"]

            result["sqrt_time"] = np.sqrt(T)
            result["inv_sqrt_time"] = 1 / np.sqrt(T.clip(lower=1 / 365))

            result["is_short_term"] = (T <= 0.25).astype(int)
            result["is_medium_term"] = ((T > 0.25) & (T <= 1.0)).astype(int)
            result["is_long_term"] = (T > 1.0).astype(int)

        return result

    def add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility surface features.

        Includes IV rank, percentile, skew, and term structure.
        """
        result = df.copy()

        if "implied_volatility" not in df.columns:
            return result

        for underlying in df["underlying"].unique():
            mask = df["underlying"] == underlying
            underlying_data = df[mask].copy()

            if len(underlying_data) < 2:
                continue

            iv = underlying_data["implied_volatility"]

            for window in self.lookback_windows:
                col_name = f"iv_rank_{window}d"
                if len(iv) >= window:
                    rolling_min = iv.rolling(window, min_periods=1).min()
                    rolling_max = iv.rolling(window, min_periods=1).max()
                    rank = (iv - rolling_min) / (rolling_max - rolling_min + 1e-8)
                    result.loc[mask, col_name] = rank

                col_name = f"iv_percentile_{window}d"
                if len(iv) >= window:
                    percentile = iv.rolling(window, min_periods=1).apply(
                        lambda x: (x.iloc[-1] <= x).sum() / len(x)
                    )
                    result.loc[mask, col_name] = percentile

            if (
                "instrument_type" in underlying_data.columns
                and "strike_price" in underlying_data.columns
            ):
                calls = underlying_data[underlying_data["instrument_type"] == "CALL"]
                puts = underlying_data[underlying_data["instrument_type"] == "PUT"]

                if len(calls) > 0 and len(puts) > 0:
                    avg_call_iv = calls.groupby("trade_date")[
                        "implied_volatility"
                    ].mean()
                    avg_put_iv = puts.groupby("trade_date")["implied_volatility"].mean()

                    skew = avg_put_iv - avg_call_iv

                    for date in skew.index:
                        date_mask = mask & (df["trade_date"] == date)
                        result.loc[date_mask, "iv_skew"] = skew[date]

        return result

    def add_market_features(
        self,
        options_df: pd.DataFrame,
        stocks_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add market microstructure features.

        Requires stocks data to calculate realized volatility and momentum.
        """
        result = options_df.copy()

        result["trade_date"] = pd.to_datetime(result["trade_date"])
        stocks_df = stocks_df.copy()
        stocks_df["trade_date"] = pd.to_datetime(stocks_df["trade_date"])

        for underlying in options_df["underlying"].unique():
            stock_data = stocks_df[stocks_df["underlying"] == underlying].copy()

            if len(stock_data) < 2:
                continue

            stock_data = stock_data.sort_values("trade_date")

            if "close_price" in stock_data.columns:
                returns = stock_data["close_price"].pct_change()

                for window in self.lookback_windows:
                    if len(returns) >= window:
                        realized_vol = returns.rolling(window).std() * np.sqrt(252)
                        stock_data[f"realized_vol_{window}d"] = realized_vol

                        momentum = stock_data["close_price"].pct_change(window)
                        stock_data[f"momentum_{window}d"] = momentum

            if "volume" in stock_data.columns:
                for window in self.lookback_windows:
                    if len(stock_data) >= window:
                        vol_ma = stock_data["volume"].rolling(window).mean()
                        stock_data[f"volume_ratio_{window}d"] = (
                            stock_data["volume"] / vol_ma
                        )

            merge_cols = ["underlying", "trade_date"]
            feature_cols = [
                col
                for col in stock_data.columns
                if any(
                    [
                        "realized_vol" in col,
                        "momentum" in col,
                        "volume_ratio" in col,
                    ]
                )
            ]

            if feature_cols:
                result = result.merge(
                    stock_data[merge_cols + feature_cols],
                    on=merge_cols,
                    how="left",
                )

        return result

    def calculate_iv_metrics(
        self,
        df: pd.DataFrame,
        groupby_cols: list[str] | None = None,
    ) -> pd.DataFrame:
        """Calculate implied volatility metrics by group.

        Args:
            df: DataFrame with implied_volatility column
            groupby_cols: Columns to group by (default: ["underlying", "trade_date"])

        Returns:
            DataFrame with IV statistics per group
        """
        if "implied_volatility" not in df.columns:
            raise ValueError("DataFrame must contain 'implied_volatility' column")

        groupby_cols = groupby_cols or ["underlying", "trade_date"]

        iv_stats = (
            df.groupby(groupby_cols)["implied_volatility"]
            .agg(
                [
                    ("iv_mean", "mean"),
                    ("iv_std", "std"),
                    ("iv_min", "min"),
                    ("iv_max", "max"),
                    ("iv_median", "median"),
                ]
            )
            .reset_index()
        )

        iv_stats["iv_range"] = iv_stats["iv_max"] - iv_stats["iv_min"]
        iv_stats["iv_cv"] = iv_stats["iv_std"] / (iv_stats["iv_mean"] + 1e-8)

        return iv_stats

    def calculate_option_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate option-specific metrics.

        Includes volume ratios, open interest, put/call ratios.
        """
        result = df.copy()

        if "volume" in df.columns:
            for underlying in df["underlying"].unique():
                mask = df["underlying"] == underlying
                underlying_data = df[mask]

                total_volume = underlying_data.groupby("trade_date")[
                    "volume"
                ].transform("sum")
                result.loc[mask, "volume_pct"] = underlying_data["volume"] / (
                    total_volume + 1e-8
                )

                if "instrument_type" in df.columns:
                    calls = underlying_data[
                        underlying_data["instrument_type"] == "CALL"
                    ]
                    puts = underlying_data[underlying_data["instrument_type"] == "PUT"]

                    call_volume = calls.groupby("trade_date")["volume"].sum()
                    put_volume = puts.groupby("trade_date")["volume"].sum()

                    pcr = put_volume / (call_volume + 1e-8)

                    for date in pcr.index:
                        date_mask = mask & (df["trade_date"] == date)
                        result.loc[date_mask, "put_call_ratio"] = pcr[date]

        return result
