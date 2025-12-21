# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.7](https://github.com/renves/b3quant/compare/b3quant-v0.1.6...b3quant-v0.1.7) (2025-12-21)


### Bug Fixes

* improve type hints and code quality ([f388120](https://github.com/renves/b3quant/commit/f3881202e65497abf564edb08dc90b6958ac2724))

## [0.1.6](https://github.com/renves/b3quant/compare/b3quant-v0.1.5...b3quant-v0.1.6) (2025-12-21)


### Features

* Aletheia - to bring out of the hidden ([ee77a8e](https://github.com/renves/b3quant/commit/ee77a8ef4bc5c28eeccc44dbdf737152ad38ab7b))
* Aletheia - to bring out of the hidden ([b7a7ca6](https://github.com/renves/b3quant/commit/b7a7ca63bfa4a14fffa9ce0d59da6b609df1486a))
* Change name of package ([a912ca3](https://github.com/renves/b3quant/commit/a912ca3355c500d50b937b35de024fe430575cad))
* initial release of pybovespa ([078cbb6](https://github.com/renves/b3quant/commit/078cbb66642551654bad7b4169f86368ea60aa09))
* release please update ([ecaebe9](https://github.com/renves/b3quant/commit/ecaebe96021ac62c39f818dd70845150bb7a8986))
* type of release ([a11cc4c](https://github.com/renves/b3quant/commit/a11cc4cbc97615cddea519932ec7a0c2e56c5bab))
* update release-please-config.json ([d3343c3](https://github.com/renves/b3quant/commit/d3343c3bfa3aefa79d2814d7ccf88535504d1585))


### Bug Fixes

* fix github links from docs ([26ed57e](https://github.com/renves/b3quant/commit/26ed57e828046862e881910063506c136a90d446))
* Fixing lint errors ([9d8665a](https://github.com/renves/b3quant/commit/9d8665a477fa2d66c24887765175fb9edabbdf91))
* Proper error handling according to lint. ([4757ef9](https://github.com/renves/b3quant/commit/4757ef925e52141223135c50d22c5a7ea02b94c9))

## [0.1.4](https://github.com/renves/b3quant/compare/b3quant-v0.1.3...b3quant-v0.1.4) (2025-12-20)


### Bug Fixes

* fix github links from docs ([26ed57e](https://github.com/renves/b3quant/commit/26ed57e828046862e881910063506c136a90d446))

## [0.1.3](https://github.com/renves/b3quant/compare/b3quant-v0.1.2...b3quant-v0.1.3) (2025-12-20)


### Bug Fixes

* Proper error handling according to lint. ([4757ef9](https://github.com/renves/b3quant/commit/4757ef925e52141223135c50d22c5a7ea02b94c9))

## [0.1.2](https://github.com/renves/b3quant/compare/b3quant-v0.1.1...b3quant-v0.1.2) (2025-12-20)


### Bug Fixes

* Fixing lint errors ([9d8665a](https://github.com/renves/b3quant/commit/9d8665a477fa2d66c24887765175fb9edabbdf91))

## [0.1.1](https://github.com/renves/b3quant/compare/b3quant-v0.1.0...b3quant-v0.1.1) (2025-12-20)


### Features

* initial release of b3quant ([078cbb6](https://github.com/renves/b3quant/commit/078cbb66642551654bad7b4169f86368ea60aa09))
* release please update ([ecaebe9](https://github.com/renves/b3quant/commit/ecaebe96021ac62c39f818dd70845150bb7a8986))
* type of release ([a11cc4c](https://github.com/renves/b3quant/commit/a11cc4cbc97615cddea519932ec7a0c2e56c5bab))
* update release-please-config.json ([d3343c3](https://github.com/renves/b3quant/commit/d3343c3bfa3aefa79d2814d7ccf88535504d1585))

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
- High-level b3quant API for simple data access
- Comprehensive test suite with 64% coverage
- GitHub Actions CI/CD pipeline
- Type hints throughout the codebase
- MIT License
- Complete documentation and examples
