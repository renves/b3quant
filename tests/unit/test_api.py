"""
Tests for B3Quant API
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from b3quant import B3Quant, get_all, get_options, get_stocks


class TestB3QuantAPI:
    """Test suite for B3Quant main API"""

    @pytest.fixture
    def b3(self, tmp_path):
        """Create B3Quant instance with temp directory"""
        return B3Quant(cache_dir=str(tmp_path))

    def test_initialization(self, tmp_path):
        """Test B3Quant initialization"""
        b3 = B3Quant(cache_dir=str(tmp_path))

        assert b3.cache_dir == tmp_path
        assert b3.downloader is not None
        assert b3.parser is not None

    def test_get_options_year(self, b3):
        """Test get_options with year parameter"""
        with patch.object(b3.downloader, "download_yearly") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_options(year=2024)

                mock_download.assert_called_once_with(2024, force=False)
                mock_parse.assert_called_once()
                assert isinstance(result, pd.DataFrame)

    def test_get_stocks_year(self, b3):
        """Test get_stocks with year parameter"""
        with patch.object(b3.downloader, "download_yearly") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_stocks(year=2024)

                mock_download.assert_called_once_with(2024, force=False)
                assert isinstance(result, pd.DataFrame)

    def test_get_all_year(self, b3):
        """Test get_all with year parameter"""
        with patch.object(b3.downloader, "download_yearly") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_all(year=2024)

                mock_download.assert_called_once_with(2024, force=False)
                assert isinstance(result, pd.DataFrame)

    def test_get_options_month(self, b3):
        """Test get_options with month parameter"""
        with patch.object(b3.downloader, "download_monthly") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_options(month=(2024, 11))

                mock_download.assert_called_once_with(2024, 11, force=False)
                assert isinstance(result, pd.DataFrame)

    def test_get_options_date_string(self, b3):
        """Test get_options with date as string"""
        with patch.object(b3.downloader, "download_daily") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_options(date="2024-12-20")

                assert mock_download.called
                assert isinstance(result, pd.DataFrame)

    def test_get_options_date_datetime(self, b3):
        """Test get_options with date as datetime"""
        with patch.object(b3.downloader, "download_daily") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_options(date=datetime(2024, 12, 20))

                assert mock_download.called
                assert isinstance(result, pd.DataFrame)

    def test_get_options_default_current_year(self, b3):
        """Test get_options defaults to current year"""
        with patch.object(b3.downloader, "download_yearly") as mock_download:
            with patch.object(b3.parser, "parse_file") as mock_parse:
                mock_download.return_value = Path("fake.txt")
                mock_parse.return_value = pd.DataFrame({"test": [1, 2, 3]})

                result = b3.get_options()

                assert mock_download.called
                call_year = mock_download.call_args[0][0]
                assert call_year == datetime.now().year


class TestConvenienceFunctions:
    """Test standalone convenience functions"""

    def test_get_options_function(self):
        """Test get_options convenience function"""
        with patch("b3quant.B3Quant") as mock_b3:
            mock_instance = Mock()
            mock_instance.get_options.return_value = pd.DataFrame({"test": [1, 2, 3]})
            mock_b3.return_value = mock_instance

            result = get_options(year=2024)

            assert mock_instance.get_options.called
            assert isinstance(result, pd.DataFrame)

    def test_get_stocks_function(self):
        """Test get_stocks convenience function"""
        with patch("b3quant.B3Quant") as mock_b3:
            mock_instance = Mock()
            mock_instance.get_stocks.return_value = pd.DataFrame({"test": [1, 2, 3]})
            mock_b3.return_value = mock_instance

            result = get_stocks(year=2024)

            assert mock_instance.get_stocks.called
            assert isinstance(result, pd.DataFrame)

    def test_get_all_function(self):
        """Test get_all convenience function"""
        with patch("b3quant.B3Quant") as mock_b3:
            mock_instance = Mock()
            mock_instance.get_all.return_value = pd.DataFrame({"test": [1, 2, 3]})
            mock_b3.return_value = mock_instance

            result = get_all(year=2024)

            assert mock_instance.get_all.called
            assert isinstance(result, pd.DataFrame)
