"""COTAHIST Parser - Fixed-width file parser for B3 historical data"""

import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from .. import config
from . import cotahist_metadata as meta

logger = logging.getLogger(__name__)


class COTAHISTParser:
    """Parse COTAHIST fixed-width format files"""

    MARKET_TYPES = meta.MARKET_TYPES

    def parse_file(
        self,
        filepath: Path | str,
        instrument_filter: Literal["options", "stocks", "all"] | None = "all",
    ) -> pd.DataFrame:
        """Parse COTAHIST file with optional instrument filtering"""
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(f"Parsing {filepath.name}...")

        chunks = []

        try:
            for chunk in pd.read_fwf(
                filepath,
                header=None,
                names=list(meta.FIELD_WIDTHS.keys()),
                widths=list(meta.FIELD_WIDTHS.values()),
                encoding=config.FILE_ENCODING,
                dtype=str,
                chunksize=config.PARSER_CHUNK_SIZE,
            ):
                chunk = chunk[chunk["record_type"] == "01"].copy()

                if len(chunk) == 0:
                    continue

                if instrument_filter == "options":
                    chunk = chunk[chunk["market_type"].isin(["070", "080"])].copy()
                elif instrument_filter == "stocks":
                    chunk = chunk[chunk["market_type"] == "010"].copy()

                if len(chunk) > 0:
                    chunks.append(chunk)

            if not chunks:
                logger.warning(f"No records found matching filter: {instrument_filter}")
                return pd.DataFrame()

            df = pd.concat(chunks, ignore_index=True)

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

        df = self._convert_types(df)
        df = self._add_derived_fields(df)

        logger.info(f"Parsed {len(df):,} records from {filepath.name}")

        return df

    def _convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert column types from strings"""
        for col in meta.PRICE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 100.0

        for col in meta.INTEGER_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

        for col in meta.DATE_COLUMNS:
            if col in df.columns:
                df[col] = df[col].replace("99991231", pd.NA)
                df[col] = pd.to_datetime(df[col], format="%Y%m%d", errors="coerce")

        for col in meta.STRING_COLUMNS:
            if col in df.columns:
                df[col] = df[col].str.strip()

        return df

    def _parse_line(self, line: str) -> dict[str, Any]:
        """Parse single line (for testing)"""
        from io import StringIO

        df = pd.read_fwf(
            StringIO(line),
            header=None,
            names=list(meta.FIELD_WIDTHS.keys()),
            widths=list(meta.FIELD_WIDTHS.values()),
            dtype=str,
        )

        df = self._convert_types(df)
        return cast(dict[str, Any], df.iloc[0].to_dict())

    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add calculated fields"""
        df["instrument_type"] = df["market_type"].map(meta.MARKET_TYPES)
        df["underlying"] = df["ticker"].str[:4]

        if "maturity_date" in df.columns and "trade_date" in df.columns:
            maturity = pd.to_datetime(df["maturity_date"])
            trade = pd.to_datetime(df["trade_date"])
            df["days_to_maturity"] = (maturity - trade).dt.days
            df["time_to_maturity"] = df["days_to_maturity"] / 365.25

        if "strike_price" in df.columns:
            df["has_strike"] = df["strike_price"] > 0

        return df

    def parse_multiple(
        self,
        filepaths: Sequence[Path | str],
        instrument_filter: Literal["options", "stocks", "all"] | None = "all",
    ) -> pd.DataFrame:
        """
        Parse multiple COTAHIST files and concatenate.

        Args:
            filepaths: List of file paths to parse
            instrument_filter: Filter by instrument type

        Returns:
            Concatenated DataFrame

        Examples:
            >>> parser = COTAHISTParser()
            >>> files = ['COTAHIST_A2020.TXT', 'COTAHIST_A2021.TXT']
            >>> df = parser.parse_multiple(files, instrument_filter='options')
        """
        dfs = []

        for filepath in filepaths:
            try:
                df = self.parse_file(filepath, instrument_filter)
                dfs.append(df)
            except Exception as e:
                logger.error(f"Failed to parse {filepath}: {e}")
                continue

        if not dfs:
            logger.warning("No files were successfully parsed")
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)

        logger.info(f"Combined {len(result):,} records from {len(dfs)} files")

        return result

    def get_options_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get summary statistics for options data.

        Args:
            df: DataFrame from parse_file()

        Returns:
            Summary DataFrame grouped by underlying asset

        Examples:
            >>> parser = COTAHISTParser()
            >>> df = parser.parse_file('COTAHIST_A2024.TXT', instrument_filter='options')
            >>> summary = parser.get_options_summary(df)
            >>> print(summary.head())
        """
        if "instrument_type" not in df.columns:
            raise ValueError("DataFrame missing 'instrument_type' column")

        options = df[df["instrument_type"].isin(["CALL", "PUT"])].copy()

        if len(options) == 0:
            logger.warning("No options found in DataFrame")
            return pd.DataFrame()

        summary = (
            options.groupby("underlying")
            .agg(
                {
                    "ticker": "count",
                    "volume": "sum",
                    "trades_count": "sum",
                    "close_price": ["min", "max", "mean"],
                    "strike_price": ["min", "max"],
                }
            )
            .round(2)
        )

        summary.columns = [
            "num_series",
            "total_volume",
            "total_trades",
            "min_premium",
            "max_premium",
            "avg_premium",
            "min_strike",
            "max_strike",
        ]

        return summary.sort_values("total_volume", ascending=False)
