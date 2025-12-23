"""
Storage backends for b3quant.

Provides efficient storage and retrieval of market data using various formats
including Parquet for columnar storage and fast analytics.
"""

from .parquet import ParquetStorage

__all__ = ["ParquetStorage"]
