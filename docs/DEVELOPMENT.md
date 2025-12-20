# Development Guide

## Prerequisites

- Python 3.10+
- UV package manager (recommended) or pip

## Setup Development Environment

### Using UV (Recommended)

```bash
# Install UV
pip install uv

# Clone repository
git clone https://github.com/renves/aletheia.git
cd aletheia

# Install dependencies (creates .venv automatically)
uv sync

# Activate virtual environment (optional, uv run does this automatically)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Using pip

```bash
# Clone repository
git clone https://github.com/renves/aletheia.git
cd aletheia

# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest -v --cov=aletheia --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_parser.py -v

# Run integration tests
uv run python teste.py
```

## Code Quality

### Linting

```bash
# Check code quality
uv run ruff check aletheia/

# Auto-fix issues
uv run ruff check --fix aletheia/

# Format code
uv run ruff format aletheia/
```

### Type Checking

```bash
# Run mypy
uv run mypy aletheia/
```

## Project Configuration

Configuration is centralized in `aletheia/config.py`:

```python
# Parser settings
PARSER_CHUNK_SIZE = 100_000  # Lines per chunk
FILE_ENCODING = 'latin1'     # COTAHIST encoding

# Downloader settings
B3_BASE_URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"
REQUEST_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
```

## Testing Strategy

### Unit Tests

Located in `tests/unit/`:
- `test_parser.py` - Parser functionality
- `test_downloader.py` - Download functionality

### Integration Tests

`teste.py` - End-to-end testing with real data

## Building Package

```bash
# Install build tools
pip install build

# Build distribution
python -m build

# Output: dist/*.tar.gz and dist/*.whl
```

## Common Tasks

### Add New Field to Parser

1. Update `aletheia/parsers/cotahist_metadata.py`:
   ```python
   FIELD_WIDTHS = {
       # ... existing fields
       'new_field': 10,  # width in characters
   }
   ```

2. Add to appropriate column list:
   ```python
   PRICE_COLUMNS = [..., 'new_field']  # if it's a price
   ```

3. Add tests in `tests/unit/test_parser.py`

### Update B3 URL or Headers

Edit `aletheia/config.py`:
```python
B3_BASE_URL = "new_url"
USER_AGENT = "new_user_agent"
```

## Release Process

Releases are automated via release-please:

1. Commit with conventional commit message
2. Push to main branch
3. Release-please creates PR with CHANGELOG
4. Merge PR triggers:
   - GitHub release creation
   - PyPI publication

See [PUBLISHING.md](PUBLISHING.md) for details.

## Troubleshooting

### Import Errors

If you get import errors, ensure you're in development mode:
```bash
pip install -e .
```

### Memory Errors with Large Files

Adjust chunk size in `config.py`:
```python
PARSER_CHUNK_SIZE = 50_000  # Reduce if needed
```

### Download Failures (CAPTCHA)

B3 may require CAPTCHA for automated downloads. Download manually from:
https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/

Then parse locally:
```python
from aletheia.parsers.cotahist import COTAHISTParser
parser = COTAHISTParser()
df = parser.parse_file('path/to/COTAHIST_A2024.TXT')
```

## Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set in config:
```python
# aletheia/config.py
LOG_LEVEL = 'DEBUG'
```

## Resources

- [B3 Historical Data](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/)
- [COTAHIST Layout Documentation](https://www.b3.com.br/data/files/33/67/B9/50/D84057102C784E47AC094EA8/SeriesHistoricas_Layout.pdf)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Release Please](https://github.com/googleapis/release-please)
