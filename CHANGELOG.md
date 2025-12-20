# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2](https://github.com/renves/pybovespa/compare/pybovespa-v0.1.1...pybovespa-v0.1.2) (2025-12-20)


### Bug Fixes

* Fixing lint errors ([9d8665a](https://github.com/renves/pybovespa/commit/9d8665a477fa2d66c24887765175fb9edabbdf91))

## [0.1.1](https://github.com/renves/pybovespa/compare/pybovespa-v0.1.0...pybovespa-v0.1.1) (2025-12-20)


### Features

* initial release of pybovespa ([078cbb6](https://github.com/renves/pybovespa/commit/078cbb66642551654bad7b4169f86368ea60aa09))
* release please update ([ecaebe9](https://github.com/renves/pybovespa/commit/ecaebe96021ac62c39f818dd70845150bb7a8986))
* type of release ([a11cc4c](https://github.com/renves/pybovespa/commit/a11cc4cbc97615cddea519932ec7a0c2e56c5bab))
* update release-please-config.json ([d3343c3](https://github.com/renves/pybovespa/commit/d3343c3bfa3aefa79d2814d7ccf88535504d1585))

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
