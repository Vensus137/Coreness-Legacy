"""
Tests for TextExtractor module
"""
import pytest
from pathlib import Path
from modules.text_extractor import TextExtractor


@pytest.mark.asyncio
class TestTextExtractor:
    """Test TextExtractor functionality"""
    
    async def test_extract_text_file(self, logger, tmp_path):
        """Test extracting text from TXT file"""
        extractor = TextExtractor(logger)
        
        test_content = "Hello, World!\nThis is a test."
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(test_content.encode('utf-8'))
        
        result = await extractor.extract_text(test_file, 'txt')
        
        assert result['result'] == 'success'
        assert result['text'] == test_content
        assert 'detected_encoding' in result['metadata']

    async def test_extract_markdown_file(self, logger, tmp_path):
        """Test extracting text from MD file"""
        extractor = TextExtractor(logger)
        
        test_content = "# Header\n\nSome **bold** text."
        test_file = tmp_path / "test.md"
        test_file.write_bytes(test_content.encode('utf-8'))
        
        result = await extractor.extract_text(test_file, 'md')
        
        assert result['result'] == 'success'
        assert result['text'] == test_content

    async def test_extract_utf8_cyrillic_and_unicode_punctuation(self, logger, tmp_path):
        """Test that UTF-8 Cyrillic and Unicode punctuation (e.g. em dash) are extracted correctly.
        chardet can misdetect such content as Windows-1252; we must try UTF-8 first."""
        extractor = TextExtractor(logger)
        
        test_content = "# Coreness — Мультитенантная платформа для автоматизации и AI-решений\n\nТекст на русском."
        test_file = tmp_path / "test.md"
        test_file.write_bytes(test_content.encode('utf-8'))
        
        result = await extractor.extract_text(test_file, 'md')
        
        assert result['result'] == 'success'
        assert result['text'] == test_content
        assert 'Мультитенантная' in result['text']
        assert '—' in result['text']
        assert result['metadata']['detected_encoding'] == 'utf-8'
    
    async def test_extract_csv_file(self, logger, tmp_path):
        """Test extracting text from CSV file (e.g. from Google Sheets export)"""
        extractor = TextExtractor(logger)
        
        test_content = "col1,col2,col3\nA,B,C\n1,2,3"
        test_file = tmp_path / "test.csv"
        test_file.write_bytes(test_content.encode('utf-8'))
        
        result = await extractor.extract_text(test_file, 'csv')
        
        assert result['result'] == 'success'
        assert result['text'] == test_content
        assert 'detected_encoding' in result['metadata']

    async def test_extract_html_file(self, logger, tmp_path):
        """Test extracting text from HTML file"""
        extractor = TextExtractor(logger)
        
        test_file = tmp_path / "test.html"
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Header</h1>
                <p>Paragraph text</p>
            </body>
        </html>
        """
        test_file.write_text(html_content, encoding='utf-8')
        
        result = await extractor.extract_text(test_file, 'html')
        
        assert result['result'] == 'success'
        assert 'Header' in result['text']
        assert 'Paragraph text' in result['text']
        assert 'tables_count' in result['metadata']
        assert result['metadata']['tables_count'] == 0
    
    async def test_unsupported_format(self, logger, tmp_path):
        """Test unsupported format handling"""
        extractor = TextExtractor(logger)
        
        test_file = tmp_path / "test.unknown"
        test_file.write_bytes(b"dummy")
        
        result = await extractor.extract_text(test_file, 'unknown')
        
        assert result['result'] == 'error'
        assert result['error']['code'] == 'UNSUPPORTED_FORMAT'
