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
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

import requests
from tqdm import tqdm

from .. import config
from ..utils.cache import CacheBackend, create_cache
from ..utils.retry import exponential_backoff_with_jitter

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

    def __init__(
        self,
        cache_dir: str = "./data/raw",
        use_metadata_cache: bool | None = None,
        show_progress: bool | None = None,
    ):
        """
        Initialize downloader.

        Args:
            cache_dir: Directory to store downloaded files
            use_metadata_cache: Enable metadata cache (default: from config)
            show_progress: Show progress bars (default: from config)
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        # Initialize metadata cache (tracks downloads with TTL)
        self.use_metadata_cache = (
            use_metadata_cache
            if use_metadata_cache is not None
            else config.CACHE_ENABLED
        )
        self.metadata_cache: CacheBackend | None
        if self.use_metadata_cache:
            backend = cast(Literal["json", "sqlite"], config.CACHE_BACKEND)
            self.metadata_cache = create_cache(
                backend=backend, cache_dir=config.CACHE_DIR
            )
            logger.debug(f"Metadata cache enabled (backend: {config.CACHE_BACKEND})")
        else:
            self.metadata_cache = None

        # Progress bar setting
        self.show_progress = (
            show_progress if show_progress is not None else config.SHOW_PROGRESS
        )

    def _is_cache_valid(self, cache_key: str, file_path: Path) -> bool:
        """
        Check if cached file is still valid.

        Args:
            cache_key: Cache metadata key
            file_path: Path to cached file

        Returns:
            True if cache is valid, False otherwise
        """
        # File must exist
        if not file_path.exists():
            return False

        # If metadata cache disabled, only check file existence
        if not self.use_metadata_cache or self.metadata_cache is None:
            return True

        # Check metadata cache for TTL
        metadata = self.metadata_cache.get(cache_key)
        if metadata is None:
            # No metadata, file may be old - re-download
            logger.debug(f"No metadata found for {cache_key}")
            return False

        logger.debug(f"Cache hit for {cache_key}")
        return True

    def _update_cache_metadata(self, cache_key: str, file_path: Path) -> None:
        """
        Update cache metadata after successful download.

        Args:
            cache_key: Cache metadata key
            file_path: Path to downloaded file
        """
        if not self.use_metadata_cache or self.metadata_cache is None:
            return

        ttl_seconds = config.CACHE_TTL_DAYS * 24 * 60 * 60
        metadata = {"file_path": str(file_path), "size": file_path.stat().st_size}

        self.metadata_cache.set(cache_key, metadata, ttl=ttl_seconds)
        logger.debug(
            f"Updated cache metadata for {cache_key} (TTL: {config.CACHE_TTL_DAYS} days)"
        )

    def _fetch_with_progress(self, url: str, zip_filename: str) -> bytearray:
        """
        Fetch file from URL with optional progress bar.

        Args:
            url: URL to download from
            zip_filename: Name of file being downloaded (for display)

        Returns:
            Downloaded content as bytearray

        Raises:
            requests.exceptions.RequestException: If download fails
        """
        response = self.session.get(url, timeout=config.REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()

        # Get total file size for progress bar
        total_size = int(response.headers.get("content-length", 0))

        # Download with optional progress bar
        content = bytearray()
        if self.show_progress and total_size > 0:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=f"Downloading {zip_filename}",
                bar_format=config.PROGRESS_BAR_FORMAT,
                colour=config.PROGRESS_BAR_COLOUR,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        content.extend(chunk)
                        pbar.update(len(chunk))
        else:
            # No progress bar
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content.extend(chunk)

        return content

    def _download_with_retry(
        self,
        url: str,
        zip_filename: str,
        txt_filename: str,
        txt_path: Path,
        max_retries: int,
    ) -> Path:
        """
        Internal method to download and extract ZIP file with retry logic.

        Uses jitter-based exponential backoff to prevent thundering herd problem.

        Args:
            url: URL to download from
            zip_filename: Name of ZIP file
            txt_filename: Expected TXT filename inside ZIP
            txt_path: Path where TXT file should be extracted
            max_retries: Maximum number of retry attempts

        Returns:
            Path to extracted TXT file

        Raises:
            requests.exceptions.RequestException: If download fails after all retries
            ValueError: If CAPTCHA is required
            FileNotFoundError: If expected file not found after extraction
        """
        import time

        last_exception = None

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Downloading {url} (attempt {attempt + 1}/{max_retries})..."
                )

                # Fetch file content with progress bar
                content = self._fetch_with_progress(url, zip_filename)

                # Check if we got HTML instead of ZIP (CAPTCHA page)
                if (
                    content[:100]
                    .decode("utf-8", errors="ignore")
                    .lower()
                    .strip()
                    .startswith("<!doctype html")
                ):
                    raise ValueError(
                        f"Received HTML instead of ZIP file. CAPTCHA may be required.\n"
                        f"Please download manually from:\n"
                        f"https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/\n"
                        f"Then use: COTAHISTParser().parse_file('path/to/{txt_filename}')"
                    )

                logger.info(f"Extracting {zip_filename}...")
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    z.extractall(self.cache_dir)

                if not txt_path.exists():
                    raise FileNotFoundError(
                        f"Expected file {txt_path} not found after extraction"
                    )

                logger.info(f"Successfully downloaded and extracted: {txt_path}")
                return txt_path

            except requests.exceptions.RequestException as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")

                if attempt < max_retries - 1:
                    # Calculate delay with jitter-based exponential backoff
                    delay = exponential_backoff_with_jitter(
                        attempt=attempt,
                        base_delay=config.RETRY_BASE_DELAY,
                        max_delay=config.RETRY_MAX_DELAY,
                        jitter=config.RETRY_JITTER,
                    )
                    logger.info(f"Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    raise

        # Fallback (should not reach here)
        if last_exception:
            raise last_exception
        raise RuntimeError("Download loop completed without returning")

    def download_yearly(
        self, year: int, force: bool = False, max_retries: int | None = None
    ) -> Path:
        """
        Download yearly COTAHIST file.

        Args:
            year: Year to download (e.g., 2024)
            force: Force re-download even if file exists in cache
            max_retries: Maximum number of retry attempts (default: from config)

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
        cache_key = f"cotahist_yearly_{year}"

        # Check cache validity (file + TTL)
        if not force and self._is_cache_valid(cache_key, txt_path):
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        result = self._download_with_retry(
            url=url,
            zip_filename=zip_filename,
            txt_filename=txt_filename,
            txt_path=txt_path,
            max_retries=max_retries or config.MAX_RETRY_ATTEMPTS,
        )

        # Update cache metadata
        self._update_cache_metadata(cache_key, result)

        return result

    def download_monthly(
        self, year: int, month: int, force: bool = False, max_retries: int | None = None
    ) -> Path:
        """
        Download monthly COTAHIST file.

        Args:
            year: Year (e.g., 2024)
            month: Month (1-12)
            force: Force re-download
            max_retries: Maximum retry attempts (default: from config)

        Returns:
            Path to extracted TXT file

        Examples:
            >>> downloader = COTAHISTDownloader()
            >>> filepath = downloader.download_monthly(2024, 12)
        """
        zip_filename = f"COTAHIST_M{month:02d}{year}.ZIP"
        txt_filename = f"COTAHIST_M{month:02d}{year}.TXT"
        txt_path = self.cache_dir / txt_filename
        cache_key = f"cotahist_monthly_{year}_{month:02d}"

        # Check cache validity (file + TTL)
        if not force and self._is_cache_valid(cache_key, txt_path):
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        result = self._download_with_retry(
            url=url,
            zip_filename=zip_filename,
            txt_filename=txt_filename,
            txt_path=txt_path,
            max_retries=max_retries or config.MAX_RETRY_ATTEMPTS,
        )

        # Update cache metadata
        self._update_cache_metadata(cache_key, result)

        return result

    def download_daily(
        self, date: datetime, force: bool = False, max_retries: int | None = None
    ) -> Path:
        """
        Download daily COTAHIST file.

        Args:
            date: Trading date
            force: Force re-download
            max_retries: Maximum retry attempts (default: from config)

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
        cache_key = f"cotahist_daily_{date_str}"

        # Check cache validity (file + TTL)
        if not force and self._is_cache_valid(cache_key, txt_path):
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{self.BASE_URL}/{zip_filename}"

        result = self._download_with_retry(
            url=url,
            zip_filename=zip_filename,
            txt_filename=txt_filename,
            txt_path=txt_path,
            max_retries=max_retries or config.MAX_RETRY_ATTEMPTS,
        )

        # Update cache metadata
        self._update_cache_metadata(cache_key, result)

        return result

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
        years = list(range(start_year, end_year + 1))

        # Use progress bar if enabled
        iterator = (
            tqdm(
                years,
                desc="Downloading years",
                unit="year",
                bar_format=config.PROGRESS_BAR_FORMAT,
                colour=config.PROGRESS_BAR_COLOUR,
            )
            if self.show_progress
            else years
        )

        for year in iterator:
            try:
                path = self.download_yearly(year)
                paths.append(path)
                if self.show_progress and isinstance(iterator, tqdm):
                    iterator.set_postfix_str(f"✓ {year}")
            except Exception as e:
                logger.error(f"Failed to download year {year}: {e}")
                if self.show_progress and isinstance(iterator, tqdm):
                    iterator.set_postfix_str(f"✗ {year}")
                if not skip_errors:
                    raise

        return paths
