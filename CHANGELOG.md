# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Centralized configuration in `config.py`
- Chunked file reading for large COTAHIST files (handles 2M+ records)
- Credits section acknowledging rb3 and b3fileparser projects
- Release-please automation for GitHub releases

### Changed
- Refactored parser to use `pd.read_fwf()` for better performance
- Improved code organization with metadata separation
- Cleaned up unnecessary comments
- Removed hardcoded values in favor of configuration constants

### Fixed
- Memory allocation errors when parsing large annual files
- Encoding issues in test scripts

## [0.1.0] - 2024-12-20

### Added
- Initial release combining rb3 download functionality with b3fileparser parsing
- COTAHIST downloader with retry logic and caching
- COTAHIST parser with support for options, stocks, and all instruments
- High-level PyBovespa API for simple data access
- Comprehensive test suite with 64% coverage
- GitHub Actions CI/CD pipeline
- Type hints throughout the codebase
- MIT License
- Complete documentation and examples
