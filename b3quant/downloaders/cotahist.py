"""
COTAHIST Downloader

Downloads historical market data files from B3 (Brazilian Stock Exchange).

Data source: https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/historical-data/equities/historical-quotes/

Available data:
- Yearly series: 1986 to current year
- Monthly series: Last 12 months
- Daily series: Current year
"""

import io
import logging
import time
import zipfile
from datetime import datetime
from pathlib import Path

import requests

from .. import config

logger = logging.getLogger(__name__)


class COTAHISTDownloader:
    """
    Download COTAHIST files from B3.

    COTAHIST files contain historical trading data for all instruments
    traded on B3, including stocks, options, and other derivatives.

    Examples:
        >>> downloader = COTAHISTDownloader(cache_dir="./data")
        >>> filepath = downloader.download_yearly(2024)
        >>> print(filepath)
        ./data/COTAHIST_A2024.TXT
    """

    BASE_URL = config.B3_BASE_URL

    HEADERS = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.b3.com.br/",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

    def __init__(self, cache_dir: str = "./data/raw"):
        """
        Initialize downloader.

        Args:
            cache_dir: Directory to store downloaded files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def download_yearly(
        self, year: int, force: bool = False, max_retries: int = 3
    ) -> Path:
        """
        Download yearly COTAHIST file.

        Args:
            year: Year to download (e.g., 2024)
            force: Force re-download even if file exists in cache
            max_retries: Maximum number of retry attempts

        Returns:
            Path to extracted TXT file

        Raises:
            requests.exceptions.RequestException: If download fails
            ValueError: If CAPTCHA is required

        Examples:
            >>> downloader = COTAHISTDownloader()
            >>> filepath = downloader.download_yearly(2024)
        """
        zip_filename = f"COTAHIST_A{year}.ZIP"
        txt_filename = f"COTAHIST_A{year}.TXT"
        txt_path = self.cache_dir / txt_filename

        if txt_path.exists() and not force:
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading {url} (attempt {attempt + 1}/{max_retries})..."
                )

                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()

                # Check if we got HTML instead of ZIP (CAPTCHA page)
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError(
                        f"Received HTML instead of ZIP file. CAPTCHA may be required.\n"
                        f"Please download manually from:\n"
                        f"https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/\n"
                        f"Then use: COTAHISTParser().parse_file('path/to/{txt_filename}')"
                    )

                logger.info(f"Extracting {zip_filename}...")
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall(self.cache_dir)

                if not txt_path.exists():
                    raise FileNotFoundError(
                        f"Expected file {txt_path} not found after extraction"
                    )

                logger.info(f"Successfully downloaded and extracted: {txt_path}")
                return txt_path

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    raise

        raise RuntimeError("Download loop completed without returning")

    def download_monthly(
        self, year: int, month: int, force: bool = False, max_retries: int = 3
    ) -> Path:
        """
        Download monthly COTAHIST file.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            force: Force re-download
            max_retries: Maximum retry attempts

        Returns:
            Path to extracted TXT file

        Examples:
            >>> downloader = COTAHISTDownloader()
            >>> filepath = downloader.download_monthly(2024, 12)
        """
        zip_filename = f"COTAHIST_M{month:02d}{year}.ZIP"
        txt_filename = f"COTAHIST_M{month:02d}{year}.TXT"
        txt_path = self.cache_dir / txt_filename

        if txt_path.exists() and not force:
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading {url} (attempt {attempt + 1}/{max_retries})..."
                )

                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError(
                        f"Received HTML instead of ZIP file. CAPTCHA may be required.\n"
                        f"Please download manually from:\n"
                        f"https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/historical-data/equities/historical-quotes/\n"
                        f"Then use: COTAHISTParser().parse_file('path/to/{txt_filename}')"
                    )

                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall(self.cache_dir)

                if not txt_path.exists():
                    raise FileNotFoundError(
                        f"Expected file {txt_path} not found after extraction"
                    )

                logger.info(f"Successfully downloaded and extracted: {txt_path}")
                return txt_path

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    raise

        raise RuntimeError("Download loop completed without returning")

    def download_daily(
        self, date: datetime, force: bool = False, max_retries: int = 3
    ) -> Path:
        """
        Download daily COTAHIST file.

        Args:
            date: Trading date
            force: Force re-download
            max_retries: Maximum retry attempts

        Returns:
            Path to extracted TXT file

        Examples:
            >>> from datetime import datetime
            >>> downloader = COTAHISTDownloader()
            >>> filepath = downloader.download_daily(datetime(2024, 12, 17))
        """
        date_str = date.strftime("%d%m%Y")
        zip_filename = f"COTAHIST_D{date_str}.ZIP"
        txt_filename = f"COTAHIST_D{date_str}.TXT"
        txt_path = self.cache_dir / txt_filename

        if txt_path.exists() and not force:
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading {url} (attempt {attempt + 1}/{max_retries})..."
                )

                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError(
                        f"Received HTML instead of ZIP file. CAPTCHA may be required.\n"
                        f"Please download manually from:\n"
                        f"https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/historical-data/equities/historical-quotes/\n"
                        f"Then use: COTAHISTParser().parse_file('path/to/{txt_filename}')"
                    )

                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    z.extractall(self.cache_dir)

                if not txt_path.exists():
                    raise FileNotFoundError(
                        f"Expected file {txt_path} not found after extraction"
                    )

                logger.info(f"Successfully downloaded and extracted: {txt_path}")
                return txt_path

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    raise

        raise RuntimeError("Download loop completed without returning")

    def download_range(
        self, start_year: int, end_year: int, skip_errors: bool = True
    ) -> list[Path]:
        """
        Download multiple years.

        Args:
            start_year: First year to download
            end_year: Last year to download (inclusive)
            skip_errors: Continue if download fails for a year

        Returns:
            List of paths to downloaded files

        Examples:
            >>> downloader = COTAHISTDownloader()
            >>> paths = downloader.download_range(2020, 2024)
            >>> print(f"Downloaded {len(paths)} files")
        """
        paths = []

        for year in range(start_year, end_year + 1):
            try:
                path = self.download_yearly(year)
                paths.append(path)
            except Exception as e:
                logger.error(f"Failed to download year {year}: {e}")
                if not skip_errors:
                    raise

        return paths
