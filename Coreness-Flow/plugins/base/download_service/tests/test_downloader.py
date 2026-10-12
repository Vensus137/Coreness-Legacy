"""
Tests for Downloader module
"""
import pytest
from pathlib import Path
from modules.downloader import Downloader


class TestDownloader:
    """Test Downloader functionality"""
    
    def test_convert_google_drive_url(self, logger, temp_downloads_dir):
        """Test Google Drive URL conversion"""
        downloader = Downloader(logger, temp_downloads_dir)
        
        # Test sharing URL
        url = "https://drive.google.com/file/d/1mXgnXctlFMa8VdfzwgVzwuheDDSEea1K/view?usp=sharing"
        converted = downloader._convert_google_drive_url(url)
        assert "uc?export=download&id=1mXgnXctlFMa8VdfzwgVzwuheDDSEea1K" in converted
        
        # Test already converted URL
        direct_url = "https://drive.google.com/uc?export=download&id=ABC123"
        assert downloader._convert_google_drive_url(direct_url) == direct_url

    def test_convert_github_url(self, logger, temp_downloads_dir):
        """Test GitHub blob URL conversion to raw file URL"""
        downloader = Downloader(logger, temp_downloads_dir)

        url = "https://github.com/Vensus137/Coreness/blob/main/README_EN.md"
        converted = downloader._convert_github_url(url)
        assert converted == "https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"

        # With path containing slashes
        url2 = "https://github.com/owner/repo/blob/master/docs/readme.md"
        assert downloader._convert_github_url(url2) == "https://raw.githubusercontent.com/owner/repo/master/docs/readme.md"

        # Non-blob URL is not converted
        assert downloader._convert_github_url("https://github.com/owner/repo") is None
        assert downloader._convert_github_url("https://example.com/file.md") is None

    def test_convert_google_docs_url(self, logger, temp_downloads_dir):
        """Test Google Docs/Sheets URL conversion"""
        downloader = Downloader(logger, temp_downloads_dir)
        
        # Test Google Docs
        docs_url = "https://docs.google.com/document/d/ABC123/edit"
        converted, file_type = downloader._convert_google_docs_url(docs_url)
        assert "export?format=txt" in converted
        assert file_type == "txt"
        
        # Test Google Sheets
        sheets_url = "https://docs.google.com/spreadsheets/d/XYZ789/edit"
        converted, file_type = downloader._convert_google_docs_url(sheets_url)
        assert "export?format=csv" in converted
        assert file_type == "csv"
    
    def test_normalize_url(self, logger, temp_downloads_dir):
        """Test URL normalization"""
        downloader = Downloader(logger, temp_downloads_dir)
        
        # Test Google Drive
        gdrive_url = "https://drive.google.com/file/d/ABC123/view"
        normalized, detected = downloader._normalize_url(gdrive_url)
        assert "uc?export=download" in normalized
        
        # Test Google Docs
        gdocs_url = "https://docs.google.com/document/d/ABC123/edit"
        normalized, detected = downloader._normalize_url(gdocs_url)
        assert detected == "txt"
        
        # Test GitHub blob URL -> raw
        github_blob = "https://github.com/Vensus137/Coreness/blob/main/README_EN.md"
        normalized, detected = downloader._normalize_url(github_blob)
        assert normalized == "https://raw.githubusercontent.com/Vensus137/Coreness/main/README_EN.md"
        assert detected is None

        # Test regular URL
        regular_url = "https://example.com/file.pdf"
        normalized, detected = downloader._normalize_url(regular_url)
        assert normalized == regular_url
        assert detected is None
    
    def test_generate_filename(self, logger, temp_downloads_dir):
        """Test filename generation"""
        downloader = Downloader(logger, temp_downloads_dir)
        url = "https://example.com/document.pdf"
        filename = downloader._generate_filename(url)
        assert ".pdf" in filename
        assert "_" in filename
        filename2 = downloader._generate_filename("https://example.com/other.pdf")
        assert filename != filename2


@pytest.mark.asyncio
class TestDownloaderAsync:
    """Test async Downloader functionality"""
    
    async def test_download_real_google_drive_file(self, logger, temp_downloads_dir):
        """Test downloading real file from Google Drive"""
        downloader = Downloader(logger, temp_downloads_dir)
        
        # Real Google Drive link (MD file)
        url = "https://drive.google.com/file/d/1mXgnXctlFMa8VdfzwgVzwuheDDSEea1K/view?usp=sharing"
        
        result = await downloader.download_file(
            url=url,
            max_size_mb=50,
            timeout_seconds=60
        )
        
        # Check success
        assert result.get('result') == 'success'
        assert 'file_path' in result
        assert 'file_size' in result
        assert 'download_timestamp' in result
        
        # Check file exists
        file_path = result['file_path']
        assert file_path.exists()
        assert file_path.stat().st_size > 0
        
        # Cleanup
        file_path.unlink()
    
    async def test_download_with_size_limit(self, logger, temp_downloads_dir):
        """Test file size limit enforcement"""
        downloader = Downloader(logger, temp_downloads_dir)
        
        # Try to download with very small limit
        url = "https://drive.google.com/file/d/1mXgnXctlFMa8VdfzwgVzwuheDDSEea1K/view?usp=sharing"
        
        result = await downloader.download_file(
            url=url,
            max_size_mb=0.001,  # 1KB limit
            timeout_seconds=60
        )
        
        # Should return error about file size
        assert result.get('result') == 'error'
        assert result.get('error', {}).get('code') == 'FILE_TOO_LARGE'
