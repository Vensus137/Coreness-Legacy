"""
Tests for FileDetector module
"""
import pytest
from pathlib import Path
from modules.file_detector import FileDetector


@pytest.mark.asyncio
class TestFileDetector:
    """Test FileDetector functionality"""
    
    async def test_detect_with_hint(self, logger, tmp_path):
        """Test detection with file type hint"""
        detector = FileDetector(logger, ['pdf', 'docx', 'txt', 'md', 'html'])
        
        # Create dummy file
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"dummy content")
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://example.com/file",
            file_type_hint="pdf"
        )
        
        assert result['result'] == 'success'
        assert result['file_type'] == 'pdf'
    
    async def test_detect_by_extension(self, logger, tmp_path):
        """Test detection by file extension"""
        detector = FileDetector(logger, ['pdf', 'docx', 'txt', 'md', 'html'])
        
        # Create file with .txt extension
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://example.com/file.txt"
        )
        
        assert result['result'] == 'success'
        assert result['file_type'] == 'txt'
    
    async def test_detect_by_content_type(self, logger, tmp_path):
        """Test detection by Content-Type header"""
        detector = FileDetector(logger, ['pdf', 'docx', 'txt', 'md', 'html'])
        
        test_file = tmp_path / "test.bin"
        test_file.write_bytes(b"dummy")
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://example.com/file",
            content_type="application/pdf"
        )
        
        assert result['result'] == 'success'
        assert result['file_type'] == 'pdf'
    
    async def test_unsupported_format(self, logger, tmp_path):
        """Test unsupported format handling"""
        detector = FileDetector(logger, ['pdf', 'txt'])
        
        test_file = tmp_path / "test.docx"
        test_file.write_bytes(b"dummy")
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://example.com/file.docx",
            file_type_hint="docx"
        )
        
        # Should return error for unsupported format
        assert result['result'] == 'error'
        assert result['error']['code'] == 'UNSUPPORTED_FORMAT'

    async def test_bin_file_with_text_content_sniffed_as_txt(self, logger, tmp_path):
        """Test that .bin file (e.g. from Google Drive) with plain text is detected as txt"""
        detector = FileDetector(logger, ['pdf', 'docx', 'txt', 'md', 'html'])
        
        test_file = tmp_path / "file.bin"
        test_file.write_text("Hello, this is plain text content.", encoding='utf-8')
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://drive.google.com/uc?export=download&id=abc123"
        )
        
        assert result['result'] == 'success'
        assert result['file_type'] == 'txt'

    async def test_bin_file_with_markdown_content_sniffed_as_md(self, logger, tmp_path):
        """Test that .bin file with markdown content is detected as md"""
        detector = FileDetector(logger, ['pdf', 'docx', 'txt', 'md', 'html'])
        
        test_file = tmp_path / "file.bin"
        test_file.write_text("# README\n\nSome markdown content.", encoding='utf-8')
        
        result = await detector.detect_file_type(
            file_path=test_file,
            url="https://drive.google.com/uc?export=download&id=abc123"
        )
        
        assert result['result'] == 'success'
        assert result['file_type'] == 'md'
