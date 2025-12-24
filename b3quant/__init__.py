"""b3quant - Python library for B3 market data"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from . import config
from .downloaders.cotahist import COTAHISTDownloader
from .parsers.cotahist import COTAHISTParser
from .parsers.cotahist_metadata import InstrumentCategory
from .storage.parquet import ParquetStorage

__version__ = "0.1.15"
__author__ = "Renan Alves"
__email__ = "renanalvees@gmail.com"

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)

logger = logging.getLogger(__name__)


class B3Quant:
    """Main interface for B3 market data"""

    def __init__(
        self,
        cache_dir: str | None = None,
        use_parquet_cache: bool | None = None,
        parquet_cache_dir: str | None = None,
    ):
        """
        Initialize B3Quant.

        Args:
            cache_dir: Directory for raw COTAHIST files
            use_parquet_cache: Enable Parquet cache for parsed data (much faster)
            parquet_cache_dir: Directory for Parquet cache
        """
        if cache_dir is None:
            cache_dir = str(config.DEFAULT_CACHE_DIR)
        self.cache_dir = Path(cache_dir)
        self.downloader = COTAHISTDownloader(cache_dir=cache_dir)
        self.parser = COTAHISTParser()

        # Parquet cache for parsed data
        if use_parquet_cache is None:
            use_parquet_cache = config.USE_PARQUET_CACHE
        self.use_parquet_cache = use_parquet_cache
        self.parquet_storage: ParquetStorage | None
        if use_parquet_cache:
            if parquet_cache_dir is None:
                parquet_cache_dir = str(self.cache_dir / config.PARQUET_CACHE_SUBDIR)
            self.parquet_storage = ParquetStorage(
                base_path=parquet_cache_dir,
                compression=config.PARQUET_COMPRESSION,  # type: ignore
            )
            logger.info(f"Parquet cache enabled at {parquet_cache_dir}")
        else:
            self.parquet_storage = None

    def get_options(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
        force_parse: bool = False,
    ) -> pd.DataFrame:
        """
        Get options data from B3.

        Args:
            year: Year to download
            month: Month to download
            day: Day to download
            force_download: Force re-download even if cached
            force_parse: Force re-parse even if Parquet cache exists

        Returns:
            DataFrame with options data
        """
        return self._get_data("options", year, month, day, force_download, force_parse)

    def get_stocks(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
        force_parse: bool = False,
    ) -> pd.DataFrame:
        """
        Get stocks data from B3.

        Args:
            year: Year to download
            month: Month to download
            day: Day to download
            force_download: Force re-download even if cached
            force_parse: Force re-parse even if Parquet cache exists

        Returns:
            DataFrame with stocks data
        """
        return self._get_data("stocks", year, month, day, force_download, force_parse)

    def get_all(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
        force_parse: bool = False,
    ) -> pd.DataFrame:
        """
        Get all instruments data from B3.

        Args:
            year: Year to download
            month: Month to download
            day: Day to download
            force_download: Force re-download even if cached
            force_parse: Force re-parse even if Parquet cache exists

        Returns:
            DataFrame with all instruments data
        """
        return self._get_data("all", year, month, day, force_download, force_parse)

    def _get_data(
        self,
        instrument_filter: Literal["options", "stocks", "all"],
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
        force_parse: bool = False,
    ) -> pd.DataFrame:
        """Internal method to get data with different filters and time periods"""
        # Default to current year if no date specified
        if year is None and month is None and day is None:
            year = datetime.now().year

        # Validate date parameters
        if day is not None and (year is None or month is None):
            raise ValueError("year and month are required when day is specified")
        if month is not None and year is None:
            raise ValueError("year is required when month is specified")

        # Try to read from Parquet cache first (if enabled and not forcing parse)
        # At this point year is guaranteed to be int due to earlier validation
        if self.use_parquet_cache and not force_parse and year is not None:
            df = self._try_read_from_parquet(instrument_filter, year, month, day)
            if df is not None:
                logger.info(
                    f"Loaded {len(df):,} rows from Parquet cache "
                    f"(year={year}, month={month}, day={day})"
                )
                return df

        # Cache miss or force_parse - download and parse
        # At this point, year is guaranteed to be int (validated above or defaulted)
        assert year is not None  # Help mypy understand year is int here
        if day is not None:
            assert month is not None  # Guaranteed by validation
            date_obj = datetime(year, month, day)
            filepath = self.downloader.download_daily(date_obj, force=force_download)
        elif month is not None:
            filepath = self.downloader.download_monthly(
                year,
                month,
                force=force_download,
            )
        else:
            filepath = self.downloader.download_yearly(year, force=force_download)

        # Parse file
        logger.info(f"Parsing {filepath.name}...")
        df = self.parser.parse_file(filepath, instrument_filter=instrument_filter)

        # Save to Parquet cache (year is guaranteed to be int at this point)
        if self.use_parquet_cache and not df.empty and year is not None:
            self._save_to_parquet(df, instrument_filter, year, month, day)

        return df

    def _try_read_from_parquet(
        self,
        instrument_filter: Literal["options", "stocks", "all"],
        year: int,
        month: int | None,
        day: int | None,
    ) -> pd.DataFrame | None:
        """Try to read data from Parquet cache."""
        if not self.parquet_storage:
            return None

        try:
            if instrument_filter == "options":
                df = self.parquet_storage.read_options(year, month, day)
            elif instrument_filter == "stocks":
                df = self.parquet_storage.read_stocks(year, month, day)
            else:
                # For "all", we need to read both and concatenate
                options_df = self.parquet_storage.read_options(year, month, day)
                stocks_df = self.parquet_storage.read_stocks(year, month, day)
                if options_df.empty and stocks_df.empty:
                    return None
                df = pd.concat([options_df, stocks_df], ignore_index=True)

            return df if not df.empty else None
        except Exception as e:
            logger.debug(f"Parquet cache miss: {e}")
            return None

    def _save_to_parquet(
        self,
        df: pd.DataFrame,
        instrument_filter: Literal["options", "stocks", "all"],
        year: int,
        month: int | None,
        day: int | None,
    ) -> None:
        """Save parsed data to Parquet cache."""
        if not self.parquet_storage:
            return

        try:
            if instrument_filter == "options":
                self.parquet_storage.write_options(df, year, month, day)
            elif instrument_filter == "stocks":
                self.parquet_storage.write_stocks(df, year, month, day)
            else:
                # For "all", save both options and stocks separately
                options_df = df[df["market_type"].isin(InstrumentCategory.OPTION.value)]
                stocks_df = df[df["market_type"] == InstrumentCategory.STOCK.value]
                if not options_df.empty:
                    self.parquet_storage.write_options(options_df, year, month, day)
                if not stocks_df.empty:
                    self.parquet_storage.write_stocks(stocks_df, year, month, day)

            logger.info(f"Saved {len(df):,} rows to Parquet cache")
        except Exception as e:
            logger.warning(f"Failed to save to Parquet cache: {e}")


def get_options(**kwargs) -> pd.DataFrame:
    """Quick access to options data"""
    return B3Quant().get_options(**kwargs)


def get_stocks(**kwargs) -> pd.DataFrame:
    """Quick access to stocks data"""
    return B3Quant().get_stocks(**kwargs)


def get_all(**kwargs) -> pd.DataFrame:
    """Quick access to all instruments data"""
    return B3Quant().get_all(**kwargs)


__all__ = [
    "B3Quant",
    "COTAHISTDownloader",
    "COTAHISTParser",
    "get_options",
    "get_stocks",
    "get_all",
]
