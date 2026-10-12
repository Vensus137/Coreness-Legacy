"""Извлечение текста из PDF, DOCX, TXT, MD, HTML, CSV."""

from pathlib import Path
from typing import Any, Dict

import chardet
import fitz  # PyMuPDF
import pandas as pd
from bs4 import BeautifulSoup
from docx import Document


class TextExtractor:
    """Извлечение текста из поддерживаемых форматов."""

    def __init__(self, logger):
        self.logger = logger

    async def extract_text(self, file_path: Path, file_type: str) -> Dict[str, Any]:
        """Извлекает текст по типу файла. Возвращает dict с text, metadata или error."""
        try:
            if file_type == 'pdf':
                return await self._extract_pdf(file_path)
            elif file_type == 'docx':
                return await self._extract_docx(file_path)
            elif file_type in ['txt', 'md', 'csv']:
                return await self._extract_text_file(file_path)
            elif file_type == 'html':
                return await self._extract_html(file_path)
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "UNSUPPORTED_FORMAT",
                        "message": f"Извлечение текста для типа '{file_type}' не реализовано"
                    }
                }

        except Exception as e:
            self.logger.error("Ошибка извлечения текста из %s: %s", file_path, e)
            return {
                "result": "error",
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": f"Ошибка извлечения текста: {e}"
                }
            }
    
    async def _extract_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Извлечение текста из PDF (PyMuPDF)."""
        try:
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())
            
            text = "\n\n".join(text_parts)
            pages_count = len(doc)
            doc.close()
            
            return {
                "result": "success",
                "text": text,
                "metadata": {
                    "pages_count": pages_count
                }
            }
        
        except Exception as e:
            self.logger.error("Ошибка извлечения PDF: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": f"Ошибка извлечения PDF: {e}"
                }
            }

    async def _extract_docx(self, file_path: Path) -> Dict[str, Any]:
        """Извлечение текста из DOCX (python-docx)."""
        try:
            doc = Document(str(file_path))
            
            # Extract paragraphs
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            text = "\n\n".join(paragraphs)
            
            return {
                "result": "success",
                "text": text,
                "metadata": {}
            }
        
        except Exception as e:
            self.logger.error("Ошибка извлечения DOCX: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": f"Ошибка извлечения DOCX: {e}"
                }
            }

    async def _extract_text_file(self, file_path: Path) -> Dict[str, Any]:
        """Извлечение текста из TXT/MD/CSV с определением кодировки."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Try UTF-8 first (dominant for web, Git, Google Drive); chardet often misdetects it as Windows-1252/ISO-8859
            try:
                text = raw_data.decode('utf-8')
                encoding = 'utf-8'
            except UnicodeDecodeError:
                detected = chardet.detect(raw_data)
                encoding = detected['encoding'] or 'utf-8'
                text = raw_data.decode(encoding, errors='replace')
            
            return {
                "result": "success",
                "text": text,
                "metadata": {
                    "detected_encoding": encoding
                }
            }
        
        except Exception as e:
            self.logger.error("Ошибка извлечения текстового файла: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": f"Ошибка извлечения текста: {e}"
                }
            }

    async def _extract_html(self, file_path: Path) -> Dict[str, Any]:
        """Извлечение текста из HTML с учётом таблиц."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove scripts, styles, and other non-content tags
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Extract tables using pandas (требует lxml; при любой ошибке — только текст без таблиц)
            tables_text = []
            tables_count = 0
            try:
                tables = pd.read_html(str(file_path))
                tables_count = len(tables)
                for idx, df in enumerate(tables):
                    table_str = df.to_string(index=False)
                    tables_text.append(f"--- Table {idx + 1} ---\n{table_str}")
            except Exception:
                pass
            
            # Extract main text
            text = soup.get_text(separator='\n', strip=True)
            
            # Combine text and tables
            if tables_text:
                tables_combined = '\n\n'.join(tables_text)
                combined_text = f"{text}\n\n{tables_combined}"
            else:
                combined_text = text
            
            return {
                "result": "success",
                "text": combined_text,
                "metadata": {
                    "tables_count": tables_count
                }
            }
        
        except Exception as e:
            self.logger.error("Ошибка извлечения HTML: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "EXTRACTION_FAILED",
                    "message": f"Ошибка извлечения HTML: {e}"
                }
            }
