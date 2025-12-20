# Contributing to aletheia

Thank you for your interest in contributing to aletheia!

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/renves/aletheia.git
cd aletheia
```

2. Install UV (if you don't have it):
```bash
pip install uv
```

3. Install dependencies:
```bash
uv sync
```

4. Run tests:
```bash
uv run pytest -v
```

## Code Quality

Before submitting a PR, ensure:

1. All tests pass:
```bash
uv run pytest -v
```

2. Code passes linter:
```bash
uv run ruff check aletheia/
```

3. Code is formatted:
```bash
uv run ruff format aletheia/
```

## Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```bash
git commit -m "feat: add support for daily COTAHIST files"
git commit -m "fix: handle missing strike prices correctly"
git commit -m "docs: update installation instructions"
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Make your changes
4. Run tests and linter
5. Commit with conventional commit message
6. Push to your fork
7. Open a Pull Request

## Project Structure

```
aletheia/
├── aletheia/
│   ├── __init__.py          # Main API
│   ├── config.py            # Configuration
│   ├── downloaders/         # Download COTAHIST files
│   │   └── cotahist.py
│   └── parsers/             # Parse COTAHIST files
│       ├── cotahist.py
│       └── cotahist_metadata.py
├── tests/
│   └── unit/                # Unit tests
├── docs/                    # Documentation
└── pyproject.toml           # Project configuration
```

## Adding New Features

When adding new features:

1. Add tests in `tests/unit/`
2. Update documentation in `README.md` or `docs/`
3. Add docstrings to all public functions
4. Update `CHANGELOG.md` if significant change

## Questions?

Open an issue for:
- Bug reports
- Feature requests
- Questions about the code

Thank you for contributing!
