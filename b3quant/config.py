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

# Option Pricing Models
IV_SOLVER_MAX_ITERATIONS = 100
IV_SOLVER_TOLERANCE = 1e-6
IV_SOLVER_MIN_VOL = 1e-4
IV_SOLVER_MAX_VOL = 5.0

# B3 Reference Rates
B3_RATES_URL = "https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-taxas-referenciais-bmf-ptBR.asp"
B3_RATES_TIMEOUT = 30
