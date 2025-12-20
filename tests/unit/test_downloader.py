"""
Tests for COTAHIST downloader
"""

import pytest
from pathlib import Path
from pybovespa.downloaders.cotahist import COTAHISTDownloader
from unittest.mock import Mock, patch, MagicMock
import requests


class TestCOTAHISTDownloader:
    """Test suite for COTAHISTDownloader"""
    
    @pytest.fixture
    def downloader(self, tmp_path):
        """Create downloader instance with temp directory"""
        return COTAHISTDownloader(cache_dir=str(tmp_path))
    
    def test_initialization(self, tmp_path):
        """Test downloader initialization"""
        downloader = COTAHISTDownloader(cache_dir=str(tmp_path))
        
        assert downloader.cache_dir == tmp_path
        assert downloader.cache_dir.exists()
        assert isinstance(downloader.session, requests.Session)
    
    def test_headers_configured(self, downloader):
        """Test that headers are configured"""
        assert 'User-Agent' in downloader.session.headers
        assert 'pybovespa' in downloader.session.headers['User-Agent']
        assert downloader.session.headers['Referer'] == 'https://www.b3.com.br/'
    
    def test_download_yearly_uses_cache(self, downloader, tmp_path):
        """Test that cached files are used"""
        # Create a fake cached file
        cached_file = tmp_path / "COTAHIST_A2024.TXT"
        cached_file.write_text("fake data")
        
        # Should return cached file without downloading
        result = downloader.download_yearly(2024, force=False)
        
        assert result == cached_file
        assert result.exists()
    
    def test_download_yearly_force_redownload(self, downloader, tmp_path):
        """Test force re-download even when cache exists"""
        # Create cached file
        cached_file = tmp_path / "COTAHIST_A2024.TXT"
        cached_file.write_text("old data")
        
        # Mock the download
        with patch.object(downloader.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.headers = {'Content-Type': 'application/zip'}
            mock_response.content = b'fake zip'
            mock_get.return_value = mock_response
            
            # This should attempt to download (will fail due to fake zip)
            with pytest.raises(Exception):
                downloader.download_yearly(2024, force=True)
    
    def test_download_range_skip_errors(self, downloader):
        """Test download_range continues on errors"""
        with patch.object(downloader, 'download_yearly') as mock_download:
            # First year succeeds, second fails, third succeeds
            mock_download.side_effect = [
                Path('file1.txt'),
                Exception('Download failed'),
                Path('file3.txt'),
            ]
            
            result = downloader.download_range(2020, 2022, skip_errors=True)
            
            assert len(result) == 2
            assert mock_download.call_count == 3
    
    def test_download_range_raise_on_error(self, downloader):
        """Test download_range raises on error when skip_errors=False"""
        with patch.object(downloader, 'download_yearly') as mock_download:
            mock_download.side_effect = Exception('Download failed')
            
            with pytest.raises(Exception):
                downloader.download_range(2020, 2022, skip_errors=False)
    
    def test_url_construction(self, downloader):
        """Test URL is constructed correctly"""
        expected_base = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist"
        assert downloader.BASE_URL == expected_base
