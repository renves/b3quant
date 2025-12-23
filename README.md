# b3quant

[![PyPI version](https://badge.fury.io/py/b3quant.svg)](https://badge.fury.io/py/b3quant)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/renves/b3quant/actions/workflows/tests.yml/badge.svg)](https://github.com/renves/b3quant/actions/workflows/tests.yml)

Python library for downloading and parsing historical market data from B3 (Brazilian Stock Exchange).

## Features

- **Download COTAHIST files** - Yearly, monthly, or daily historical data
- **Parse to pandas DataFrames** - Clean, typed data ready for analysis
- **Filter by instrument type** - Options, stocks, or all instruments
- **Command Line Interface** - Terminal-based access with rich output and progress tracking
- **Async downloads** - Concurrent downloads for 5x faster multi-year data fetching
- **Parallel parsing** - Multi-core processing for 3-4x faster parsing of large files
- **Parquet data lake** - Efficient columnar storage with partitioning and compression
- **Simple, Pythonic API** - Intuitive interface
- **Type hints** - Full type annotations for better IDE support
- **Smart caching with TTL** - JSON or SQLite cache backends with automatic expiration
- **Retry with exponential backoff** - Automatic retry with jitter to handle network failures
- **Progress bars** - Visual feedback for long-running downloads
- **Black-Scholes pricing** - Option pricing and Greeks calculation
- **No R dependencies** - Pure Python implementation  

## Installation

### From PyPI (Recommended)

```bash
pip install b3quant
```

### From Source (Development)

If you cloned the repository:

```bash
git clone https://github.com/renves/b3quant.git
cd b3quant
pip install -e .
```

Or using `uv`:

```bash
git clone https://github.com/renves/b3quant.git
cd b3quant
uv sync
uv run python your_script.py
```

## Quick Start

```python
import b3quant as pyb

# Get all options traded in 2024
options = pyb.get_options(year=2024)

# Get options from November 2024
options_nov = pyb.get_options(year=2024, month=11)

# Get options from a specific day
options_day = pyb.get_options(year=2024, month=12, day=20)

# Filter by underlying asset
petr_options = options[options['underlying'] == 'PETR']

# Get specific columns
print(options[['ticker', 'strike_price', 'close_price', 'volume']].head())
```

## Usage

### Basic Usage

```python
from b3quant import B3Quant

# Initialize
b3 = B3Quant()

# Get options for a single year
options_2024 = b3.get_options(year=2024)

# Get options for a specific month
options_nov = b3.get_options(year=2024, month=11)

# Get options for a specific day
options_day = b3.get_options(year=2024, month=12, day=20)

# Get stocks data
stocks_2024 = b3.get_stocks(year=2024)
stocks_nov = b3.get_stocks(year=2024, month=11)
stocks_day = b3.get_stocks(year=2024, month=12, day=20)

# Get all instruments
all_data = b3.get_all(year=2024)
```

### Working with Options Data

```python
import b3quant as pyb

# Get options
options = pyb.get_options(year=2024)

# Filter by type
calls = options[options['instrument_type'] == 'CALL']
puts = options[options['instrument_type'] == 'PUT']

# Filter by underlying
petr_options = options[options['underlying'] == 'PETR']

# Get options near expiration
short_term = options[options['days_to_maturity'] <= 30]

# Calculate moneyness (requires underlying price)
# You'll need to merge with stocks data or calculate separately
```

### Advanced: Enrich with Underlying Prices

```python
import b3quant as pyb

# Get options and stocks from a specific month
options = pyb.get_options(year=2024, month=11)
stocks = pyb.get_stocks(year=2024, month=11)

# Merge to get underlying prices
options_enriched = options.merge(
    stocks[['underlying', 'trade_date', 'close_price']],
    left_on=['underlying', 'trade_date'],
    right_on=['underlying', 'trade_date'],
    how='left',
    suffixes=('', '_underlying')
)

# Calculate moneyness
options_enriched['moneyness'] = (
    options_enriched['close_price_underlying'] /
    options_enriched['strike_price']
)

# Filter ATM options (at-the-money)
atm_options = options_enriched[
    (options_enriched['moneyness'] >= 0.95) &
    (options_enriched['moneyness'] <= 1.05)
]
```

### Custom Cache Directory

```python
from b3quant import B3Quant

# Use custom cache directory
b3 = B3Quant(cache_dir="./my_data_cache")
options = b3.get_options(year=2024)
```

### Force Re-download

```python
# Force re-download even if file exists in cache
options = b3.get_options(year=2024, force_download=True)
```

### Cache Configuration

b3quant supports two cache backends with automatic TTL (Time-To-Live) expiration:

```python
from b3quant import B3Quant
from b3quant.downloaders.cotahist import COTAHISTDownloader

# Use JSON cache (default, human-readable)
downloader = COTAHISTDownloader(
    cache_dir="./data/raw",
    use_metadata_cache=True  # Default: True
)

# Files are cached for 30 days by default
# Configure in b3quant.config.CACHE_TTL_DAYS

# Disable progress bars if needed
downloader = COTAHISTDownloader(show_progress=False)

# Download multiple years with progress bar
paths = downloader.download_range(2020, 2024)
```

**Cache Backends:**
- **JSON** (default): Simple, human-readable, good for small datasets
- **SQLite**: More efficient for large datasets and concurrent access

Configure in `b3quant/config.py`:
```python
CACHE_BACKEND = "json"  # or "sqlite"
CACHE_TTL_DAYS = 30     # Cache expiration in days
```

### Automatic Retry

Downloads automatically retry on failure using exponential backoff with jitter:

```python
# Automatic retry is built-in
# Default: 3 attempts with exponential backoff
downloader = COTAHISTDownloader()
path = downloader.download_yearly(2024)  # Retries automatically on failure

# Customize retry attempts
path = downloader.download_yearly(2024, max_retries=5)
```

**Retry Strategy:**
- Exponential backoff: delays increase exponentially (1s, 2s, 4s, ...)
- Jitter: random delay to prevent thundering herd problem
- Configurable in `b3quant.config`: `MAX_RETRY_ATTEMPTS`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`

### Command Line Interface (CLI)

b3quant provides a full-featured CLI for terminal-based workflows:

```bash
# Download 2024 options data
b3quant download --year 2024

# Download November 2024 stocks
b3quant download --year 2024 --month 11 --instrument stocks

# Download multiple years
b3quant download --start-year 2020 --end-year 2024

# Export to Parquet
b3quant download --year 2024 --output-format parquet --output-dir ./data

# Show configuration
b3quant info
```

**CLI Features:**
- Rich terminal output with tables and colors
- Progress bars for downloads
- Data summaries after download
- Export to CSV or Parquet
- Configurable cache directory

### Async Downloads

Download multiple years concurrently for 5x performance improvement:

```python
import asyncio
from b3quant.downloaders.async_cotahist import AsyncCOTAHISTDownloader

async def main():
    downloader = AsyncCOTAHISTDownloader(max_concurrent=5)

    # Download multiple years concurrently
    paths = await downloader.download_range(2020, 2024)
    print(f"Downloaded {len(paths)} files")

asyncio.run(main())

# Or use synchronous wrapper
from b3quant.downloaders.async_cotahist import download_range_sync
paths = download_range_sync(2020, 2024)
```

**Performance:** 5x faster for downloading 5 years of data (concurrent vs sequential)

### Parallel Parser

Parse large files using multiple CPU cores for 3-4x speed improvement:

```python
from b3quant.parsers.parallel_parser import ParallelCOTAHISTParser

# Use all CPU cores
parser = ParallelCOTAHISTParser()
df = parser.parse_file('COTAHIST_A2024.TXT', instrument_filter='options')

# Specify number of workers
parser = ParallelCOTAHISTParser(n_workers=4)
df = parser.parse_file('COTAHIST_A2024.TXT')

# Parse multiple files
files = ['COTAHIST_A2023.TXT', 'COTAHIST_A2024.TXT']
df = parser.parse_multiple_files(files, instrument_filter='options')
```

**Performance:** 3-4x faster on multi-core CPUs for files with millions of records

### Parquet Data Lake

Store and query data efficiently using Parquet format:

```python
from b3quant.storage import ParquetStorage

# Initialize storage
storage = ParquetStorage(base_path='./data/lake')

# Write partitioned data
storage.write_options(options_df, year=2024, month=11)

# Read data
df = storage.read_options(year=2024, month=11)

# Read specific columns (column pruning)
df = storage.read_options(year=2024, columns=['ticker', 'close_price'])

# Read with filters (predicate pushdown)
df = storage.read_options(
    year=2024,
    filters=[('underlying', '=', 'PETR')]
)

# Get storage statistics
stats = storage.get_stats('options')
print(f"Partitions: {stats['partitions']}")
print(f"Total size: {stats['total_size_mb']:.2f} MB")
print(f"Row count: {stats['row_count']:,}")
```

**Benefits:**
- 10-20x smaller file size vs CSV
- Faster queries with column pruning and predicate pushdown
- Partitioned by year/month/day for efficient access
- Compression options: snappy (default), gzip, zstd

## DataFrame Schema

### Options Data

| Column | Type | Description |
|--------|------|-------------|
| `record_type` | str | Record type code |
| `trade_date` | date | Trading date |
| `ticker` | str | Option ticker (e.g., PETRL255) |
| `instrument_type` | str | CALL or PUT |
| `underlying` | str | Underlying asset code (e.g., PETR) |
| `company_name` | str | Company name |
| `strike_price` | float | Strike price in BRL |
| `maturity_date` | date | Expiration date |
| `open_price` | float | Opening premium |
| `high_price` | float | Highest premium |
| `low_price` | float | Lowest premium |
| `close_price` | float | Closing premium |
| `avg_price` | float | Average premium |
| `volume` | float | Trading volume in BRL |
| `trades_count` | int | Number of trades |
| `quantity` | int | Contracts traded |
| `days_to_maturity` | int | Days until expiration |
| `time_to_maturity` | float | Years until expiration |

### Stocks Data

Similar schema but without strike_price, maturity_date, and option-specific fields.

## Options Pricing

b3quant includes a Black-Scholes pricing model for European options with full Greeks calculation.

### Black-Scholes Pricing

```python
from b3quant.models.black_scholes import BlackScholes
import numpy as np

# Initialize model
bs = BlackScholes()

# Price a call option
call_price = bs.price(
    S=100,           # Spot price
    K=100,           # Strike price
    T=1.0,           # Time to maturity (years)
    r=0.05,          # Risk-free rate
    sigma=0.2,       # Volatility
    option_type='call'
)
print(f"Call price: {call_price:.2f}")  # 10.45

# Calculate Greeks
delta = bs.delta(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type='call')
gamma = bs.gamma(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
vega = bs.vega(S=100, K=100, T=1.0, r=0.05, sigma=0.2)
theta = bs.theta(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type='call')
rho = bs.rho(S=100, K=100, T=1.0, r=0.05, sigma=0.2, option_type='call')

print(f"Delta: {delta:.4f}")    # 0.6368
print(f"Gamma: {gamma:.4f}")    # 0.0199
print(f"Vega: {vega:.4f}")      # 39.79
print(f"Theta: {theta:.4f}")    # -6.41
print(f"Rho: {rho:.4f}")        # 53.23
```

### Vectorized Pricing

The Black-Scholes model supports vectorized operations for efficient bulk calculations:

```python
import numpy as np
from b3quant.models.black_scholes import BlackScholes

bs = BlackScholes()

# Price multiple strikes at once
strikes = np.array([95, 100, 105])
prices = bs.price(S=100, K=strikes, T=1.0, r=0.05, sigma=0.2, option_type='call')
print(prices)  # [13.04, 10.45, 8.24]

# Calculate Greeks for entire option chain
deltas = bs.delta(S=100, K=strikes, T=1.0, r=0.05, sigma=0.2, option_type='call')
print(deltas)  # [0.7112, 0.6368, 0.5596]
```

### Dividends Support

```python
# Price with continuous dividend yield
call_price = bs.price(
    S=100, K=100, T=1.0, r=0.05, sigma=0.2,
    q=0.02,  # 2% dividend yield
    option_type='call'
)
```

## Examples

### Example 1: Calculate Implied Volatility Surface

```python
import b3quant as pyb
import pandas as pd

# Get PETR4 options
options = pyb.get_options(year=2024)
petr_opts = options[options['underlying'] == 'PETR'].copy()

# Filter valid data
petr_opts = petr_opts[
    (petr_opts['close_price'] > 0) &
    (petr_opts['volume'] > 0) &
    (petr_opts['days_to_maturity'] > 0)
]

# You would then calculate IV using Black-Scholes
# (requires additional libraries like scipy)
# ... your IV calculation here ...
```

### Example 2: Analyze Option Volume by Strike

```python
import b3quant as pyb
import matplotlib.pyplot as plt

options = pyb.get_options(year=2024)

# Filter PETR4 calls expiring in January 2025
petr_calls = options[
    (options['underlying'] == 'PETR') &
    (options['instrument_type'] == 'CALL') &
    (options['maturity_date'] >= '2025-01-01') &
    (options['maturity_date'] < '2025-02-01')
]

# Group by strike
volume_by_strike = petr_calls.groupby('strike_price')['volume'].sum()

# Plot
volume_by_strike.plot(kind='bar', figsize=(12, 6))
plt.title('PETR4 Call Options Volume by Strike (Jan 2025)')
plt.xlabel('Strike Price')
plt.ylabel('Volume (BRL)')
plt.show()
```

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed development setup and guidelines.

Quick start:

```bash
# Clone and setup
git clone https://github.com/renves/b3quant.git
cd b3quant
uv sync

# Run tests
uv run pytest -v

# Lint code
uv run ruff check b3quant/
```

## CAPTCHA Handling

B3 sometimes requires CAPTCHA for downloads. If automatic download fails:

1. **Download manually** from [B3 website](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/)
2. **Save to cache directory** (default: `./data/raw/`)
3. **Parse the file** directly:

```python
from b3quant.parsers.cotahist import COTAHISTParser

parser = COTAHISTParser()
options = parser.parse_file('path/to/COTAHIST_A2024.TXT', instrument_filter='options')
```

## Data Source

All data comes from B3 (Brasil, Bolsa, Balcão) official historical data files.

**Official B3 Data Page**: https://www.b3.com.br/en_us/market-data-and-indices/data-services/market-data/historical-data/equities/historical-quotes/

**Available Data**:
- **Yearly series**: 1986 to current year (COTAHIST_A{YEAR}.ZIP)
- **Monthly series**: Last 12 months (COTAHIST_M{MM}{YEAR}.ZIP)
- **Daily series**: Current year (COTAHIST_D{DDMMYYYY}.ZIP)

**Format Details**:
- Format: COTAHIST (fixed-width text format, 245 bytes per line)
- Update frequency: Daily
- Historical depth: Since 1986
- License: Data is publicly available from B3
- Encoding: Latin-1

## Contributing

Contributions are welcome! See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed guidelines.

Quick summary:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Make your changes and add tests
4. Run tests and linter
5. Commit with [conventional commits](https://www.conventionalcommits.org/) format
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This library is not affiliated with or endorsed by B3. It is an independent project for educational and research purposes.

Market data provided by B3 is subject to their terms of use. Please review B3's data policies before using this library for commercial purposes.

## Credits

This library was inspired by and builds upon the work of:

- **[rb3](https://github.com/wilsonfreitas/rb3)** by Wilson Freitas - R package for downloading B3 data
- **[b3fileparser](https://github.com/coliveira2001/b3fileparser)** by Carlos Oliveira - Python parser for COTAHIST files

b3quant combines the functionality of both libraries into a unified, Pythonic interface with additional features and optimizations.

## Citation

If you use this library in your research, please cite:

```bibtex
@software{b3quant2024,
  author = {Renan Alves},
  title = {b3quant: Python library for B3 market data},
  year = {2024},
  url = {https://github.com/renves/b3quant}
}
```

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) - Setup and development workflow
- [Contributing Guide](docs/CONTRIBUTING.md) - How to contribute
- [Publishing Guide](docs/PUBLISHING.md) - Release and publishing process
- [Changelog](CHANGELOG.md) - Version history

## Support

- 🐛 [Issue Tracker](https://github.com/renves/b3quant/issues)
- 💬 [Discussions](https://github.com/renves/b3quant/discussions)
