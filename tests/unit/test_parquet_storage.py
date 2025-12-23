"""Tests for Parquet storage backend."""

import pandas as pd
import pytest

from b3quant.storage.parquet import ParquetStorage


@pytest.fixture
def storage(tmp_path):
    """Create ParquetStorage instance with temporary directory."""
    return ParquetStorage(base_path=tmp_path / "parquet")


@pytest.fixture
def sample_options_df():
    """Create sample options DataFrame."""
    return pd.DataFrame(
        {
            "ticker": ["PETRH230", "PETRH245", "VALET230"],
            "instrument_type": ["CALL", "CALL", "PUT"],
            "underlying": ["PETR", "PETR", "VALE"],
            "strike_price": [23.0, 24.5, 23.0],
            "close_price": [2.5, 1.8, 3.2],
            "volume": [150000.0, 120000.0, 80000.0],
            "trade_date": pd.to_datetime(["2024-11-15", "2024-11-15", "2024-11-15"]),
        }
    )


@pytest.fixture
def sample_stocks_df():
    """Create sample stocks DataFrame."""
    return pd.DataFrame(
        {
            "ticker": ["PETR4", "VALE3", "ITUB4"],
            "company_name": ["PETROBRAS", "VALE", "ITAU"],
            "close_price": [38.5, 65.2, 28.9],
            "volume": [500000.0, 400000.0, 300000.0],
            "trade_date": pd.to_datetime(["2024-11-15", "2024-11-15", "2024-11-15"]),
        }
    )


class TestParquetStorageWrite:
    """Test writing data to Parquet storage."""

    def test_write_options_yearly(self, storage, sample_options_df):
        """Test writing yearly options data."""
        path = storage.write_options(sample_options_df, year=2024)

        assert path.exists()
        assert "year=2024" in str(path)
        assert path.name == "data.parquet"

    def test_write_options_monthly(self, storage, sample_options_df):
        """Test writing monthly options data."""
        path = storage.write_options(sample_options_df, year=2024, month=11)

        assert path.exists()
        assert "year=2024" in str(path)
        assert "month=11" in str(path)

    def test_write_options_daily(self, storage, sample_options_df):
        """Test writing daily options data."""
        path = storage.write_options(sample_options_df, year=2024, month=11, day=15)

        assert path.exists()
        assert "year=2024" in str(path)
        assert "month=11" in str(path)
        assert "day=15" in str(path)

    def test_write_stocks(self, storage, sample_stocks_df):
        """Test writing stocks data."""
        path = storage.write_stocks(sample_stocks_df, year=2024, month=11)

        assert path.exists()
        assert "stocks" in str(path)


class TestParquetStorageRead:
    """Test reading data from Parquet storage."""

    def test_read_options_yearly(self, storage, sample_options_df):
        """Test reading yearly options data."""
        storage.write_options(sample_options_df, year=2024)
        df = storage.read_options(year=2024)

        assert len(df) == len(sample_options_df)
        assert list(df.columns) == list(sample_options_df.columns)

    def test_read_options_monthly(self, storage, sample_options_df):
        """Test reading monthly options data."""
        storage.write_options(sample_options_df, year=2024, month=11)
        df = storage.read_options(year=2024, month=11)

        assert len(df) == len(sample_options_df)

    def test_read_options_with_columns(self, storage, sample_options_df):
        """Test reading specific columns."""
        storage.write_options(sample_options_df, year=2024)
        df = storage.read_options(year=2024, columns=["ticker", "close_price"])

        assert len(df) == len(sample_options_df)
        assert list(df.columns) == ["ticker", "close_price"]

    def test_read_options_with_filters(self, storage, sample_options_df):
        """Test reading with filters (predicate pushdown)."""
        storage.write_options(sample_options_df, year=2024)
        df = storage.read_options(year=2024, filters=[("underlying", "=", "PETR")])

        assert len(df) == 2  # Only PETR options
        assert all(df["underlying"] == "PETR")

    def test_read_nonexistent_partition(self, storage):
        """Test reading from nonexistent partition returns empty DataFrame."""
        df = storage.read_options(year=2099)

        assert df.empty


class TestParquetStoragePartitions:
    """Test partition management."""

    def test_list_partitions_empty(self, storage):
        """Test listing partitions when storage is empty."""
        partitions = storage.list_partitions("options")

        assert partitions == []

    def test_list_partitions_yearly(self, storage, sample_options_df):
        """Test listing yearly partitions."""
        storage.write_options(sample_options_df, year=2024)
        partitions = storage.list_partitions("options")

        assert len(partitions) == 1
        assert partitions[0] == {"year": 2024, "month": None, "day": None}

    def test_list_partitions_monthly(self, storage, sample_options_df):
        """Test listing monthly partitions."""
        storage.write_options(sample_options_df, year=2024, month=11)
        storage.write_options(sample_options_df, year=2024, month=12)
        partitions = storage.list_partitions("options")

        assert len(partitions) == 2
        assert {"year": 2024, "month": 11, "day": None} in partitions
        assert {"year": 2024, "month": 12, "day": None} in partitions

    def test_list_partitions_daily(self, storage, sample_options_df):
        """Test listing daily partitions."""
        storage.write_options(sample_options_df, year=2024, month=11, day=15)
        storage.write_options(sample_options_df, year=2024, month=11, day=16)
        partitions = storage.list_partitions("options")

        assert len(partitions) == 2
        assert {"year": 2024, "month": 11, "day": 15} in partitions


class TestParquetStorageStats:
    """Test storage statistics."""

    def test_get_stats_empty(self, storage):
        """Test stats for empty storage."""
        stats = storage.get_stats("options")

        assert stats["partitions"] == 0
        assert stats["total_size_mb"] == 0
        assert stats["row_count"] == 0
        assert stats["compression"] == "snappy"

    def test_get_stats_with_data(self, storage, sample_options_df):
        """Test stats with data."""
        storage.write_options(sample_options_df, year=2024, month=11)
        stats = storage.get_stats("options")

        assert stats["partitions"] == 1
        assert stats["total_size_mb"] > 0
        assert stats["row_count"] == len(sample_options_df)


class TestParquetStorageCompression:
    """Test different compression algorithms."""

    @pytest.mark.parametrize("compression", ["snappy", "gzip", "zstd"])
    def test_compression_algorithms(self, tmp_path, sample_options_df, compression):
        """Test different compression algorithms."""
        storage = ParquetStorage(base_path=tmp_path / compression, compression=compression)
        path = storage.write_options(sample_options_df, year=2024)

        assert path.exists()

        # Read back and verify data integrity
        df = storage.read_options(year=2024)
        assert len(df) == len(sample_options_df)


class TestParquetStorageIntegration:
    """Integration tests for Parquet storage."""

    def test_write_read_round_trip(self, storage, sample_options_df):
        """Test complete write-read round trip."""
        # Write data
        storage.write_options(sample_options_df, year=2024, month=11)

        # Read back
        df = storage.read_options(year=2024, month=11)

        # Verify
        assert len(df) == len(sample_options_df)
        pd.testing.assert_frame_equal(
            df[["ticker", "underlying", "strike_price"]],
            sample_options_df[["ticker", "underlying", "strike_price"]],
        )

    def test_multiple_partitions(self, storage, sample_options_df):
        """Test handling multiple partitions."""
        # Write to different months
        storage.write_options(sample_options_df, year=2024, month=11)
        storage.write_options(sample_options_df, year=2024, month=12)

        # Read all data for year
        df_nov = storage.read_options(year=2024, month=11)
        df_dec = storage.read_options(year=2024, month=12)

        assert len(df_nov) == len(sample_options_df)
        assert len(df_dec) == len(sample_options_df)
