"""b3quant - Python library for B3 market data"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from . import config
from .downloaders.cotahist import COTAHISTDownloader
from .parsers.cotahist import COTAHISTParser

__version__ = "0.1.13"
__author__ = "Renan Alves"
__email__ = "renanalvees@gmail.com"

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT)

logger = logging.getLogger(__name__)


class B3Quant:
    """Main interface for B3 market data"""

    def __init__(self, cache_dir: str | None = None):
        if cache_dir is None:
            cache_dir = str(config.DEFAULT_CACHE_DIR)
        self.cache_dir = Path(cache_dir)
        self.downloader = COTAHISTDownloader(cache_dir=cache_dir)
        self.parser = COTAHISTParser()

    def get_options(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Get options data from B3"""
        return self._get_data("options", year, month, day, force_download)

    def get_stocks(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Get stocks data from B3"""
        return self._get_data("stocks", year, month, day, force_download)

    def get_all(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Get all instruments data from B3"""
        return self._get_data("all", year, month, day, force_download)

    def _get_data(
        self,
        instrument_filter: Literal["options", "stocks", "all"],
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Internal method to get data with different filters and time periods"""
        if day is not None:
            if year is None or month is None:
                raise ValueError("year and month are required when day is specified")
            date_obj = datetime(year, month, day)
            filepath = self.downloader.download_daily(date_obj, force=force_download)
            return self.parser.parse_file(filepath, instrument_filter=instrument_filter)

        elif month is not None:
            if year is None:
                raise ValueError("year is required when month is specified")
            filepath = self.downloader.download_monthly(
                year, month, force=force_download
            )
            return self.parser.parse_file(filepath, instrument_filter=instrument_filter)

        elif year is not None:
            filepath = self.downloader.download_yearly(year, force=force_download)
            return self.parser.parse_file(filepath, instrument_filter=instrument_filter)

        else:
            return self._get_data(
                instrument_filter,
                year=datetime.now().year,
                force_download=force_download,
            )


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
