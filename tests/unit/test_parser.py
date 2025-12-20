"""
Tests for COTAHIST parser
"""


import pandas as pd
import pytest

from pybovespa.parsers.cotahist import COTAHISTParser


class TestCOTAHISTParser:
    """Test suite for COTAHISTParser"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return COTAHISTParser()

    @pytest.fixture
    def sample_line(self):
        """Sample COTAHIST line (option)"""
        # This is a realistic COTAHIST line for a PETR4 call option
        # Note: strike_price at position 188-201 is 0000000002558 = 25.58
        return "012025121778PETRL255    070PETRE       PN      N2000R$  000000000290000000000029020000000002897000000000290100000000029020000000000000000000000000000004000000000000009800000000000028438500000000000255802025121900000010000000000000BRPETRACNPR6220"

    def test_parse_line(self, parser, sample_line):
        """Test parsing a single line"""
        record = parser._parse_line(sample_line)

        assert record['record_type'] == '01'
        assert record['ticker'] == 'PETRL255'
        assert record['market_type'] == '070'  # Call option
        assert record['close_price'] == 29.02
        assert record['strike_price'] == 25.58

    def test_market_type_mapping(self, parser):
        """Test market type code mapping"""
        assert parser.MARKET_TYPES['010'] == 'STOCK'
        assert parser.MARKET_TYPES['070'] == 'CALL'
        assert parser.MARKET_TYPES['080'] == 'PUT'

    def test_add_derived_fields(self, parser):
        """Test addition of derived fields"""
        df = pd.DataFrame([
            {
                'ticker': 'PETRL255',
                'market_type': '070',
                'strike_price': 30.0,
                'trade_date': pd.Timestamp('2024-12-17').date(),
                'maturity_date': pd.Timestamp('2025-01-17').date(),
            }
        ])

        result = parser._add_derived_fields(df)

        assert 'instrument_type' in result.columns
        assert result['instrument_type'].iloc[0] == 'CALL'
        assert 'underlying' in result.columns
        assert result['underlying'].iloc[0] == 'PETR'
        assert 'days_to_maturity' in result.columns
        assert result['days_to_maturity'].iloc[0] == 31

    def test_parse_file_not_found(self, parser):
        """Test error handling for non-existent file"""
        with pytest.raises(FileNotFoundError):
            parser.parse_file('nonexistent.txt')

    def test_instrument_filter_options(self, parser, tmp_path):
        """Test filtering for options only"""
        # Create a test file with mixed instruments
        test_file = tmp_path / "test.txt"

        # Stock line (010)
        stock_line = "012025121702PETR4       010PETROBRAS   PN      N2   R$  000000000308600000000031080000000003082000000000309500000000031080000000003107000000000310841804000000000039337100000000121770129400000000000000009999123100000010000000000000BRPETRACNPR6222" + " " * 23 + "\n"

        # Option line (070)
        option_line = "012025121778PETRL255    070PETROBRAS   PN      N2000R$  000000000029020000000002902000000000290200000000029020000000002902000000000000000000000000000004000000000000028438500000000002843850000000025580202602190000000010000000000000BRPETRACNPR6222" + " " * 23 + "\n"

        with open(test_file, 'w', encoding='latin1') as f:
            f.write(stock_line)
            f.write(option_line)

        df = parser.parse_file(test_file, instrument_filter='options')

        # Should only have the option
        assert len(df) == 1
        assert df['market_type'].iloc[0] == '070'

    def test_parse_multiple_empty_list(self, parser):
        """Test parse_multiple with empty file list"""
        result = parser.parse_multiple([])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
