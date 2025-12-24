"""
b3quant Configuration
Centralized configuration constants
"""

from pathlib import Path

# Parser
PARSER_CHUNK_SIZE = 100_000
FILE_ENCODING = "latin1"

# Downloader
B3_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"
DEFAULT_CACHE_DIR = Path("./data/raw")
REQUEST_TIMEOUT = 30
USER_AGENT = "b3quant/0.1.0"

# Retry Strategy (Exponential Backoff with Jitter)
MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0  # Base delay in seconds
RETRY_MAX_DELAY = 60.0  # Maximum delay cap in seconds
RETRY_JITTER = True  # Add random jitter to prevent thundering herd

# Cache Settings
CACHE_BACKEND = "json"  # Cache backend: "json" or "sqlite"
CACHE_DIR = Path("./data/cache")  # Cache directory
CACHE_TTL_DAYS = 30  # Default TTL for cached files (days)
CACHE_ENABLED = True  # Enable/disable caching globally

# Parquet Cache Settings (for parsed data)
USE_PARQUET_CACHE = True  # Enable Parquet cache for parsed data (much faster reads)
PARQUET_CACHE_SUBDIR = "parquet"  # Subdirectory under cache_dir for Parquet files
PARQUET_COMPRESSION = "snappy"  # Compression algorithm: "snappy", "gzip", "zstd"

# Progress Bar Settings
SHOW_PROGRESS = True  # Show progress bars for downloads
PROGRESS_BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
PROGRESS_BAR_COLOUR = "green"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Validation
MIN_FILE_SIZE = 1_000
COTAHIST_LINE_LENGTH = 245

# Option Pricing Models - Implied Volatility Solver
IV_SOLVER_MAX_ITERATIONS = 100  # Maximum iterations for Newton-Raphson
IV_SOLVER_TOLERANCE = 1e-6  # Price error tolerance
IV_SOLVER_MIN_VOL = 1e-4  # Minimum volatility (0.01%)
IV_SOLVER_MAX_VOL = 5.0  # Maximum volatility (500%)
IV_INTRINSIC_MARGIN = 0.001  # Margin above intrinsic value for ITM filter (BRL)

# B3 Reference Rates
B3_RATES_URL = "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp"
B3_RATES_TIMEOUT = 30
