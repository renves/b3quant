"""
Parquet storage backend for b3quant data lake.

Provides efficient columnar storage using Parquet format with partitioning
for fast queries and analytics. Similar to rb3's approach but with Python.

Features:
- Partitioned storage (year/month/day)
- Fast column-based queries
- Compression (snappy, gzip, zstd)
- Schema evolution support
- Incremental updates

Examples:
    >>> from b3quant.storage import ParquetStorage
    >>>
    >>> # Initialize storage
    >>> storage = ParquetStorage(base_path="./data/parquet")
    >>>
    >>> # Write options data
    >>> storage.write_options(df, year=2024, month=11)
    >>>
    >>> # Read back
    >>> df = storage.read_options(year=2024, month=11)
    >>>
    >>> # Query across multiple periods
    >>> df = storage.read_options(year=2024)  # All months in 2024
"""

import logging
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class ParquetStorage:
    """
    Parquet-based data lake for B3 market data.

    Stores data in partitioned Parquet files for efficient querying and analysis.
    Supports both options and stocks data with automatic schema management.

    Examples:
        >>> storage = ParquetStorage(base_path="./data/lake")
        >>> storage.write_options(options_df, year=2024, month=11)
        >>> df = storage.read_options(year=2024, month=11)
    """

    def __init__(
        self,
        base_path: str | Path = "./data/parquet",
        compression: Literal["snappy", "gzip", "zstd", "none"] = "snappy",
    ):
        """
        Initialize Parquet storage.

        Args:
            base_path: Base directory for parquet files
            compression: Compression algorithm (snappy is fastest, zstd is smallest)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.compression = compression

        # Create subdirectories for data organization
        self.options_path = self.base_path / "options"
        self.stocks_path = self.base_path / "stocks"
        self.options_path.mkdir(exist_ok=True)
        self.stocks_path.mkdir(exist_ok=True)

    def write_options(
        self,
        df: pd.DataFrame,
        year: int,
        month: int | None = None,
        day: int | None = None,
    ) -> Path:
        """
        Write options data to partitioned Parquet files.

        Args:
            df: Options DataFrame
            year: Year
            month: Month (optional, for monthly partitioning)
            day: Day (optional, for daily partitioning)

        Returns:
            Path to written parquet file

        Examples:
            >>> storage.write_options(df, year=2024, month=11)
            PosixPath('data/parquet/options/year=2024/month=11/data.parquet')
        """
        return self._write_data(df, "options", year, month, day)

    def write_stocks(
        self,
        df: pd.DataFrame,
        year: int,
        month: int | None = None,
        day: int | None = None,
    ) -> Path:
        """
        Write stocks data to partitioned Parquet files.

        Args:
            df: Stocks DataFrame
            year: Year
            month: Month (optional)
            day: Day (optional)

        Returns:
            Path to written parquet file
        """
        return self._write_data(df, "stocks", year, month, day)

    def read_options(
        self,
        year: int,
        month: int | None = None,
        day: int | None = None,
        columns: list[str] | None = None,
        filters: list | None = None,
    ) -> pd.DataFrame:
        """
        Read options data from Parquet storage.

        Args:
            year: Year to read
            month: Month to read (None = all months)
            day: Day to read (None = all days)
            columns: List of columns to read (None = all columns)
            filters: PyArrow filters for predicate pushdown

        Returns:
            DataFrame with options data

        Examples:
            >>> # Read all 2024 options
            >>> df = storage.read_options(year=2024)
            >>>
            >>> # Read November 2024 only
            >>> df = storage.read_options(year=2024, month=11)
            >>>
            >>> # Read specific columns
            >>> df = storage.read_options(year=2024, columns=['ticker', 'close_price'])
            >>>
            >>> # Filter with predicate pushdown
            >>> df = storage.read_options(
            ...     year=2024,
            ...     filters=[('underlying', '=', 'PETR')]
            ... )
        """
        return self._read_data("options", year, month, day, columns, filters)

    def read_stocks(
        self,
        year: int,
        month: int | None = None,
        day: int | None = None,
        columns: list[str] | None = None,
        filters: list | None = None,
    ) -> pd.DataFrame:
        """
        Read stocks data from Parquet storage.

        Args:
            year: Year to read
            month: Month to read (None = all months)
            day: Day to read (None = all days)
            columns: List of columns to read
            filters: PyArrow filters

        Returns:
            DataFrame with stocks data
        """
        return self._read_data("stocks", year, month, day, columns, filters)

    def list_partitions(
        self, data_type: Literal["options", "stocks"] = "options"
    ) -> list[dict]:
        """
        List available partitions in storage.

        Args:
            data_type: Type of data ('options' or 'stocks')

        Returns:
            List of partition dictionaries with year/month/day

        Examples:
            >>> partitions = storage.list_partitions('options')
            >>> print(partitions)
            [
                {'year': 2024, 'month': 11, 'day': None},
                {'year': 2024, 'month': 12, 'day': None},
            ]
        """
        base = self.options_path if data_type == "options" else self.stocks_path
        partitions = []

        for year_dir in sorted(base.glob("year=*")):
            year = int(year_dir.name.split("=")[1])

            # Check for month partitions
            month_dirs = list(year_dir.glob("month=*"))
            if month_dirs:
                for month_dir in sorted(month_dirs):
                    month = int(month_dir.name.split("=")[1])

                    # Check for day partitions
                    day_dirs = list(month_dir.glob("day=*"))
                    if day_dirs:
                        for day_dir in sorted(day_dirs):
                            day = int(day_dir.name.split("=")[1])
                            partitions.append(
                                {"year": year, "month": month, "day": day}
                            )
                    else:
                        partitions.append({"year": year, "month": month, "day": None})  # type: ignore[dict-item]
            else:
                partitions.append({"year": year, "month": None, "day": None})  # type: ignore[dict-item]

        return partitions

    def get_stats(self, data_type: Literal["options", "stocks"] = "options") -> dict:
        """
        Get storage statistics.

        Args:
            data_type: Type of data ('options' or 'stocks')

        Returns:
            Dictionary with storage statistics

        Examples:
            >>> stats = storage.get_stats('options')
            >>> print(stats)
            {
                'partitions': 12,
                'total_size_mb': 1234.5,
                'row_count': 1500000
            }
        """
        partitions = self.list_partitions(data_type)
        base = self.options_path if data_type == "options" else self.stocks_path

        total_size = sum(f.stat().st_size for f in base.rglob("*.parquet"))

        # Count rows by reading metadata
        total_rows = 0
        for parquet_file in base.rglob("*.parquet"):
            try:
                metadata = pq.read_metadata(parquet_file)
                total_rows += metadata.num_rows
            except Exception as e:
                logger.warning(f"Could not read metadata from {parquet_file}: {e}")

        return {
            "partitions": len(partitions),
            "total_size_mb": total_size / (1024 * 1024),
            "row_count": total_rows,
            "compression": self.compression,
        }

    def _write_data(
        self,
        df: pd.DataFrame,
        data_type: Literal["options", "stocks"],
        year: int,
        month: int | None,
        day: int | None,
    ) -> Path:
        """Internal method to write data with partitioning."""
        base = self.options_path if data_type == "options" else self.stocks_path

        # Build partition path
        partition_path = base / f"year={year}"

        if month is not None:
            partition_path = partition_path / f"month={month:02d}"

        if day is not None:
            partition_path = partition_path / f"day={day:02d}"

        partition_path.mkdir(parents=True, exist_ok=True)

        # Write parquet file
        file_path = partition_path / "data.parquet"

        # Convert to PyArrow Table for better control
        table = pa.Table.from_pandas(df)

        # Write with compression
        pq.write_table(
            table,
            file_path,
            compression=self.compression,
            use_dictionary=True,  # Better compression for string columns
            write_statistics=True,  # Enable column statistics for faster queries
        )

        logger.info(
            f"Wrote {len(df):,} rows to {file_path} "
            f"(size: {file_path.stat().st_size / 1024:.2f} KB)"
        )

        return file_path

    def _read_data(
        self,
        data_type: Literal["options", "stocks"],
        year: int,
        month: int | None,
        day: int | None,
        columns: list[str] | None,
        filters: list | None,
    ) -> pd.DataFrame:
        """Internal method to read data with optional filtering."""
        base = self.options_path if data_type == "options" else self.stocks_path

        # Build partition path
        partition_path = base / f"year={year}"

        if month is not None:
            partition_path = partition_path / f"month={month:02d}"

        if day is not None:
            partition_path = partition_path / f"day={day:02d}"

        # Check if partition exists
        if not partition_path.exists():
            logger.warning(f"Partition not found: {partition_path}")
            return pd.DataFrame()

        # Read parquet file(s)
        parquet_files = list(partition_path.rglob("*.parquet"))

        if not parquet_files:
            logger.warning(f"No parquet files found in {partition_path}")
            return pd.DataFrame()

        # Read with PyArrow for better performance
        tables = []
        for file_path in parquet_files:
            table = pq.read_table(
                file_path,
                columns=columns,
                filters=filters,
                use_threads=True,  # Parallel reading
            )
            tables.append(table)

        # Concatenate if multiple files
        if len(tables) > 1:
            combined_table = pa.concat_tables(tables)
        else:
            combined_table = tables[0]

        # Convert to pandas
        df = combined_table.to_pandas()

        logger.info(f"Read {len(df):,} rows from {partition_path}")

        return df  # type: ignore[no-any-return]
