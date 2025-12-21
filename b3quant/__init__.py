"""b3quant - Python library for B3 market data"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config
from .downloaders.cotahist import COTAHISTDownloader
from .parsers.cotahist import COTAHISTParser

__version__ = "0.1.4"
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
        years: tuple[int, int] | None = None,
        force_download: bool = False,
    ) -> pd.DataFrame:
        """Get options data from B3"""
        if year:
            filepath = self.downloader.download_yearly(year, force=force_download)
            return self.parser.parse_file(filepath, instrument_filter="options")
        elif years:
            filepaths = self.downloader.download_range(years[0], years[1])
            return self.parser.parse_multiple(filepaths, instrument_filter="options")
        else:
            return self.get_options(year=datetime.now().year)


def get_options(**kwargs) -> pd.DataFrame:
    """Quick access to options data"""
    return B3Quant().get_options(**kwargs)


__all__ = ["B3Quant", "COTAHISTDownloader", "COTAHISTParser", "get_options"]
