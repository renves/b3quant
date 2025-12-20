# PyBovespa

[![PyPI version](https://badge.fury.io/py/pybovespa.svg)](https://badge.fury.io/py/pybovespa)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/yourusername/pybovespa/workflows/tests/badge.svg)](https://github.com/yourusername/pybovespa/actions)

Python library for downloading and parsing historical market data from B3 (Brazilian Stock Exchange).

## Features

- **Download COTAHIST files** - Yearly or daily historical data
- **Parse to pandas DataFrames** - Clean, typed data ready for analysis
- **Filter by instrument type** - Options, stocks, or all instruments
- **Simple, Pythonic API** - Intuitive interface
- **Type hints** - Full type annotations for better IDE support
- **Caching** - Avoid redundant downloads
- **No R dependencies** - Pure Python implementation  

## Installation

```bash
pip install pybovespa
```

## Quick Start

```python
import pybovespa as pyb

# Get all options traded in 2024
options = pyb.get_options(year=2024)

# Filter by underlying asset
petr_options = options[options['underlying'] == 'PETR']

# Get specific columns
print(options[['ticker', 'strike_price', 'close_price', 'volume']].head())
```

## Usage

### Basic Usage

```python
from pybovespa import PyBovespa

# Initialize
b3 = PyBovespa()

# Get options for a single year
options_2024 = b3.get_options(year=2024)

# Get options for multiple years
options_historical = b3.get_options(years=(2020, 2024))

# Get stocks data
stocks_2024 = b3.get_stocks(year=2024)

# Get all instruments
all_data = b3.get_all(year=2024)
```

### Working with Options Data

```python
import pybovespa as pyb

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
from pybovespa import PyBovespa

b3 = PyBovespa()

# Get options and stocks
options = b3.get_options(year=2024)
stocks = b3.get_stocks(year=2024)

# Merge to get underlying prices
options_enriched = options.merge(
    stocks[['ticker', 'trade_date', 'close_price']],
    left_on=['underlying', 'trade_date'],
    right_on=['ticker', 'trade_date'],
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
from pybovespa import PyBovespa

# Use custom cache directory
b3 = PyBovespa(cache_dir="./my_data_cache")
options = b3.get_options(year=2024)
```

### Force Re-download

```python
# Force re-download even if file exists in cache
options = b3.get_options(year=2024, force_download=True)
```

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

## Examples

### Example 1: Calculate Implied Volatility Surface

```python
import pybovespa as pyb
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
import pybovespa as pyb
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
git clone https://github.com/yourusername/pybovespa.git
cd pybovespa
uv sync

# Run tests
uv run pytest -v

# Lint code
uv run ruff check pybovespa/
```

## CAPTCHA Handling

B3 sometimes requires CAPTCHA for downloads. If automatic download fails:

1. **Download manually** from [B3 website](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/)
2. **Save to cache directory** (default: `./data/raw/`)
3. **Parse the file** directly:

```python
from pybovespa.parsers.cotahist import COTAHISTParser

parser = COTAHISTParser()
options = parser.parse_file('path/to/COTAHIST_A2024.TXT', instrument_filter='options')
```

## Data Source

All data comes from B3 (Brasil, Bolsa, Balcão) official historical data files.

- Format: COTAHIST (fixed-width text format, 245 bytes per line)
- Update frequency: Daily
- Historical depth: Since 1986
- License: Data is publicly available from B3

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

PyBovespa combines the functionality of both libraries into a unified, Pythonic interface with additional features and optimizations.

## Citation

If you use this library in your research, please cite:

```bibtex
@software{pybovespa2024,
  author = {Renan Alves},
  title = {PyBovespa: Python library for B3 market data},
  year = {2024},
  url = {https://github.com/yourusername/pybovespa}
}
```

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) - Setup and development workflow
- [Contributing Guide](docs/CONTRIBUTING.md) - How to contribute
- [Publishing Guide](docs/PUBLISHING.md) - Release and publishing process
- [Changelog](CHANGELOG.md) - Version history

## Support

- 🐛 [Issue Tracker](https://github.com/yourusername/pybovespa/issues)
- 💬 [Discussions](https://github.com/yourusername/pybovespa/discussions)
