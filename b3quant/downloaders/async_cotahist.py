"""
Asynchronous COTAHIST downloader using httpx.

Provides concurrent download capabilities for multiple years of data,
significantly improving performance when downloading large datasets.

Examples:
    >>> import asyncio
    >>> from b3quant.downloaders.async_cotahist import AsyncCOTAHISTDownloader
    >>>
    >>> async def main():
    ...     downloader = AsyncCOTAHISTDownloader()
    ...     paths = await downloader.download_range(2020, 2024)
    ...     print(f"Downloaded {len(paths)} files")
    >>>
    >>> asyncio.run(main())
"""

import asyncio
import logging
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
from tqdm.asyncio import tqdm

from .. import config
from ..utils.retry import exponential_backoff_with_jitter

logger = logging.getLogger(__name__)


class AsyncCOTAHISTDownloader:
    """
    Asynchronous downloader for COTAHIST files from B3.

    Provides concurrent download capabilities using httpx and asyncio,
    significantly faster than synchronous downloads for multiple files.

    Examples:
        >>> import asyncio
        >>> downloader = AsyncCOTAHISTDownloader()
        >>> paths = asyncio.run(downloader.download_range(2020, 2024))
    """

    def __init__(
        self,
        cache_dir: str = "./data/raw",
        max_concurrent: int = 5,
        show_progress: bool = True,
    ):
        """
        Initialize async downloader.

        Args:
            cache_dir: Directory to cache downloaded files
            max_concurrent: Maximum concurrent downloads
            show_progress: Show progress bars
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self.show_progress = show_progress

        # HTTP headers
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def download_yearly(
        self,
        year: int,
        force_download: bool = False,
        max_retries: int = 3,
    ) -> Path:
        """
        Download yearly COTAHIST file asynchronously.

        Args:
            year: Year to download
            force_download: Force re-download even if cached
            max_retries: Maximum retry attempts

        Returns:
            Path to downloaded TXT file

        Examples:
            >>> import asyncio
            >>> downloader = AsyncCOTAHISTDownloader()
            >>> path = asyncio.run(downloader.download_yearly(2024))
        """
        zip_filename = f"COTAHIST_A{year}.ZIP"
        txt_filename = f"COTAHIST_A{year}.TXT"
        txt_path = self.cache_dir / txt_filename

        # Check cache
        if txt_path.exists() and not force_download:
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        # Download with retry
        url = f"{config.B3_BASE_URL}/{zip_filename}"

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    headers=self.headers,
                    timeout=config.REQUEST_TIMEOUT,
                    follow_redirects=True,
                ) as client:
                    logger.info(f"Downloading {zip_filename} (attempt {attempt + 1})")

                    response = await client.get(url)
                    response.raise_for_status()

                    # Check for CAPTCHA
                    if "captcha" in response.text.lower():
                        raise ValueError(
                            "CAPTCHA required. Please download manually from B3 website."
                        )

                    # Extract ZIP
                    with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                        zip_file.extractall(self.cache_dir)

                    logger.info(f"Downloaded and extracted: {txt_filename}")
                    return txt_path

            except (httpx.HTTPError, zipfile.BadZipFile) as e:
                if attempt < max_retries - 1:
                    delay = exponential_backoff_with_jitter(
                        attempt,
                        base_delay=config.RETRY_BASE_DELAY,
                        max_delay=config.RETRY_MAX_DELAY,
                        jitter=config.RETRY_JITTER,
                    )
                    logger.warning(
                        f"Download failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise RuntimeError(
                        f"Failed to download {zip_filename} after {max_retries} attempts"
                    ) from e

        raise RuntimeError(f"Failed to download {zip_filename}")

    async def download_monthly(
        self,
        year: int,
        month: int,
        force_download: bool = False,
        max_retries: int = 3,
    ) -> Path:
        """
        Download monthly COTAHIST file asynchronously.

        Args:
            year: Year
            month: Month (1-12)
            force_download: Force re-download
            max_retries: Maximum retry attempts

        Returns:
            Path to downloaded TXT file
        """
        zip_filename = f"COTAHIST_M{month:02d}{year}.ZIP"
        txt_filename = f"COTAHIST_M{month:02d}{year}.TXT"
        txt_path = self.cache_dir / txt_filename

        if txt_path.exists() and not force_download:
            logger.info(f"Using cached file: {txt_path}")
            return txt_path

        url = f"{config.B3_BASE_URL}/{zip_filename}"

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    headers=self.headers,
                    timeout=config.REQUEST_TIMEOUT,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(url)
                    response.raise_for_status()

                    if "captcha" in response.text.lower():
                        raise ValueError("CAPTCHA required")

                    with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                        zip_file.extractall(self.cache_dir)

                    logger.info(f"Downloaded: {txt_filename}")
                    return txt_path

            except (httpx.HTTPError, zipfile.BadZipFile) as e:
                if attempt < max_retries - 1:
                    delay = exponential_backoff_with_jitter(attempt)
                    await asyncio.sleep(delay)
                else:
                    raise RuntimeError(f"Failed to download {zip_filename}") from e

        raise RuntimeError(f"Failed to download {zip_filename}")

    async def download_range(
        self,
        start_year: int,
        end_year: int,
        force_download: bool = False,
        max_retries: int = 3,
    ) -> list[Path]:
        """
        Download multiple years concurrently.

        Args:
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            force_download: Force re-download
            max_retries: Maximum retry attempts per file

        Returns:
            List of paths to downloaded files

        Examples:
            >>> import asyncio
            >>> downloader = AsyncCOTAHISTDownloader()
            >>> paths = asyncio.run(downloader.download_range(2020, 2024))
            >>> print(f"Downloaded {len(paths)} files")
        """
        years = list(range(start_year, end_year + 1))

        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_semaphore(year: int) -> Path:
            async with semaphore:
                return await self.download_yearly(year, force_download, max_retries)

        # Download concurrently with progress bar
        if self.show_progress:
            tasks = [download_with_semaphore(year) for year in years]
            paths = []
            for coro in tqdm.as_completed(
                tasks,
                total=len(years),
                desc="Downloading files",
                unit="file",
            ):
                path = await coro
                paths.append(path)
            return paths
        else:
            return await asyncio.gather(
                *[download_with_semaphore(year) for year in years]
            )

    async def download_multiple_months(
        self,
        year: int,
        months: list[int],
        force_download: bool = False,
        max_retries: int = 3,
    ) -> list[Path]:
        """
        Download multiple months concurrently.

        Args:
            year: Year
            months: List of months to download
            force_download: Force re-download
            max_retries: Maximum retry attempts

        Returns:
            List of paths to downloaded files
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_semaphore(month: int) -> Path:
            async with semaphore:
                return await self.download_monthly(
                    year, month, force_download, max_retries
                )

        if self.show_progress:
            tasks = [download_with_semaphore(month) for month in months]
            paths = []
            for coro in tqdm.as_completed(
                tasks,
                total=len(months),
                desc=f"Downloading {year} months",
                unit="file",
            ):
                path = await coro
                paths.append(path)
            return paths
        else:
            return await asyncio.gather(
                *[download_with_semaphore(month) for month in months]
            )


# Convenience function for synchronous code
def download_range_sync(
    start_year: int,
    end_year: int,
    cache_dir: str = "./data/raw",
    force_download: bool = False,
    max_concurrent: int = 5,
) -> list[Path]:
    """
    Synchronous wrapper for async download_range.

    Args:
        start_year: Start year
        end_year: End year
        cache_dir: Cache directory
        force_download: Force re-download
        max_concurrent: Max concurrent downloads

    Returns:
        List of downloaded file paths

    Examples:
        >>> paths = download_range_sync(2020, 2024)
        >>> print(f"Downloaded {len(paths)} files")
    """
    downloader = AsyncCOTAHISTDownloader(
        cache_dir=cache_dir,
        max_concurrent=max_concurrent,
    )
    return asyncio.run(downloader.download_range(start_year, end_year, force_download))
