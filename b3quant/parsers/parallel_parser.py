"""
Parallel COTAHIST parser for faster processing of large files.

Uses multiprocessing to parse chunks in parallel, significantly improving
performance for large COTAHIST files (millions of records).

Examples:
    >>> from b3quant.parsers.parallel_parser import ParallelCOTAHISTParser
    >>>
    >>> parser = ParallelCOTAHISTParser(n_workers=4)
    >>> df = parser.parse_file('COTAHIST_A2024.TXT', instrument_filter='options')
    >>> print(f"Parsed {len(df):,} records")
"""

import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

import pandas as pd
from tqdm import tqdm

from .. import config
from . import cotahist_metadata as meta
from .cotahist import COTAHISTParser

logger = logging.getLogger(__name__)


def _process_chunk(  # noqa: C901
    chunk_data: tuple[pd.DataFrame, str | None],
) -> pd.DataFrame:
    """
    Process a single chunk (worker function for multiprocessing).

    Args:
        chunk_data: Tuple of (chunk_df, instrument_filter)

    Returns:
        Processed DataFrame chunk
    """
    chunk, instrument_filter = chunk_data

    # Filter by record type
    chunk = chunk[chunk["record_type"] == "01"].copy()

    if len(chunk) == 0:
        return pd.DataFrame()

    # Apply instrument filter
    if instrument_filter == "options":
        market_types = ["070", "080"]
        chunk = chunk[chunk["market_type"].isin(market_types)].copy()
    elif instrument_filter == "stocks":
        market_types = ["010"]
        chunk = chunk[chunk["market_type"].isin(market_types)].copy()

    if len(chunk) == 0:
        return pd.DataFrame()

    # Type conversions
    for col in meta.PRICE_COLUMNS:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce") / 100

    for col in meta.INTEGER_COLUMNS:
        if col in chunk.columns:
            chunk[col] = (
                pd.to_numeric(chunk[col], errors="coerce").fillna(0).astype(int)
            )

    for col in meta.STRING_COLUMNS:
        if col in chunk.columns:
            chunk[col] = chunk[col].str.strip()

    for col in meta.DATE_COLUMNS:
        if col in chunk.columns:
            chunk[col] = pd.to_datetime(chunk[col], format="%Y%m%d", errors="coerce")
            # Handle missing dates (99991231)
            chunk.loc[chunk[col].dt.year == 9999, col] = pd.NaT

    # Add derived fields
    parser = COTAHISTParser()
    chunk = parser._add_derived_fields(chunk)

    return chunk


class ParallelCOTAHISTParser(COTAHISTParser):
    """
    Parallel parser for COTAHIST files using multiprocessing.

    Processes file chunks in parallel for significantly faster parsing
    of large files. Falls back to sequential processing for small files
    or when n_workers=1.

    Examples:
        >>> parser = ParallelCOTAHISTParser(n_workers=4)
        >>> df = parser.parse_file('COTAHIST_A2024.TXT', instrument_filter='options')
    """

    def __init__(
        self,
        n_workers: int | None = None,
        show_progress: bool = True,
        chunk_size: int | None = None,
    ):
        """
        Initialize parallel parser.

        Args:
            n_workers: Number of worker processes (None = CPU count)
            show_progress: Show progress bar
            chunk_size: Chunk size for reading (None = use config default)
        """
        super().__init__()
        self.n_workers = n_workers or mp.cpu_count()
        self.show_progress = show_progress
        self.chunk_size = chunk_size or config.PARSER_CHUNK_SIZE

    def parse_file(  # noqa: C901
        self,
        filepath: Path | str,
        instrument_filter: Literal["options", "stocks", "all"] | None = "all",
    ) -> pd.DataFrame:
        """
        Parse COTAHIST file with parallel processing.

        Args:
            filepath: Path to COTAHIST file
            instrument_filter: Filter by instrument type

        Returns:
            Parsed DataFrame

        Examples:
            >>> parser = ParallelCOTAHISTParser(n_workers=4)
            >>> df = parser.parse_file('COTAHIST_A2024.TXT', instrument_filter='options')
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(f"Parsing {filepath.name} with {self.n_workers} workers...")

        # For small files or single worker, use sequential processing
        if self.n_workers == 1:
            return super().parse_file(filepath, instrument_filter)

        # Read and collect chunks
        chunks_data = []
        try:
            chunk_reader = pd.read_fwf(
                filepath,
                header=None,
                names=list(meta.FIELD_WIDTHS.keys()),
                widths=list(meta.FIELD_WIDTHS.values()),
                encoding=config.FILE_ENCODING,
                dtype=str,
                chunksize=self.chunk_size,
            )

            # Collect all chunks first (for progress tracking)
            if self.show_progress:
                # Estimate total chunks based on file size
                file_size = filepath.stat().st_size
                # Rough estimate: 245 bytes per line
                estimated_lines = file_size // 245
                estimated_chunks = max(1, estimated_lines // self.chunk_size)

                with tqdm(
                    total=estimated_chunks,
                    desc="Reading chunks",
                    unit="chunk",
                ) as pbar:
                    for chunk in chunk_reader:
                        chunks_data.append((chunk, instrument_filter))
                        pbar.update(1)
            else:
                for chunk in chunk_reader:
                    chunks_data.append((chunk, instrument_filter))

        except Exception as e:
            logger.error(f"Error reading file: {e}")
            raise

        if not chunks_data:
            logger.warning("No data found in file")
            return pd.DataFrame()

        # Process chunks in parallel
        processed_chunks = []

        with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
            # Submit all chunks
            futures = {
                executor.submit(_process_chunk, chunk_data): i
                for i, chunk_data in enumerate(chunks_data)
            }

            # Collect results with progress bar
            if self.show_progress:
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="Processing chunks",
                    unit="chunk",
                ):
                    try:
                        result = future.result()
                        if not result.empty:
                            processed_chunks.append(result)
                    except Exception as e:
                        chunk_idx = futures[future]
                        logger.error(f"Error processing chunk {chunk_idx}: {e}")
            else:
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if not result.empty:
                            processed_chunks.append(result)
                    except Exception as e:
                        chunk_idx = futures[future]
                        logger.error(f"Error processing chunk {chunk_idx}: {e}")

        # Concatenate results
        if not processed_chunks:
            logger.warning("No records found after filtering")
            return pd.DataFrame()

        logger.info(f"Concatenating {len(processed_chunks)} chunks...")
        df = pd.concat(processed_chunks, ignore_index=True)

        logger.info(f"Parsed {len(df):,} records from {filepath.name}")

        return df

    def parse_multiple_files(
        self,
        filepaths: list[Path | str],
        instrument_filter: Literal["options", "stocks", "all"] | None = "all",
    ) -> pd.DataFrame:
        """
        Parse multiple COTAHIST files in parallel.

        Args:
            filepaths: List of file paths
            instrument_filter: Filter by instrument type

        Returns:
            Combined DataFrame from all files

        Examples:
            >>> parser = ParallelCOTAHISTParser()
            >>> files = ['COTAHIST_A2023.TXT', 'COTAHIST_A2024.TXT']
            >>> df = parser.parse_multiple_files(files, instrument_filter='options')
        """
        all_dfs = []

        if self.show_progress:
            iterator = tqdm(filepaths, desc="Parsing files", unit="file")  # type: ignore[assignment]
        else:
            iterator = filepaths  # type: ignore[assignment]

        for filepath in iterator:
            try:
                df = self.parse_file(filepath, instrument_filter)
                if not df.empty:
                    all_dfs.append(df)
            except Exception as e:
                logger.error(f"Error parsing {filepath}: {e}")
                continue

        if not all_dfs:
            logger.warning("No data parsed from any file")
            return pd.DataFrame()

        logger.info(f"Concatenating data from {len(all_dfs)} files...")
        combined_df = pd.concat(all_dfs, ignore_index=True)

        logger.info(f"Total records: {len(combined_df):,}")

        return combined_df
