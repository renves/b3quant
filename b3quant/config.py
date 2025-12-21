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
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2
USER_AGENT = "b3quant/0.1.0"

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Validation
MIN_FILE_SIZE = 1_000
COTAHIST_LINE_LENGTH = 245
