"""Определение типа файла по magic bytes, Content-Type или расширению."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import filetype


class FileDetector:
    """Определение типа файла: magic bytes → Content-Type → расширение."""

    def __init__(self, logger, supported_formats: List[str]):
        self.logger = logger
        self.supported_formats = supported_formats
        self.mime_to_ext = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',  # old format, not supported but detected
            'text/plain': 'txt',
            'text/markdown': 'md',
            'text/html': 'html',
            'application/xhtml+xml': 'html',
            'text/csv': 'csv',
            'application/csv': 'csv'
        }
    
    def _sniff_text_file(self, file_path: Path, sample_size: int = 8192) -> Optional[str]:
        """Пытается определить plain text или markdown по сэмплу. Возвращает 'txt', 'md' или None."""
        try:
            with open(file_path, 'rb') as f:
                raw = f.read(sample_size)
            if not raw:
                return None
            # Reject if too many null bytes (binary)
            if raw.count(b'\x00') > len(raw) // 4:
                return None
            text = raw.decode('utf-8', errors='strict')
            # Basic heuristic: if starts with # or contains ##, treat as markdown
            stripped = text.lstrip()
            if stripped.startswith('#') or '\n## ' in stripped[:500]:
                return 'md' if 'md' in self.supported_formats else 'txt'
            return 'txt'
        except (ValueError, OSError):
            return None

    async def detect_file_type(self, file_path: Path, url: str, content_type: Optional[str] = None,
                               file_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """Определяет тип файла. Возвращает dict с file_type или error."""
        try:
            detected_type = None
            
            # 0. Use hint if provided and supported
            if file_type_hint:
                if file_type_hint in self.supported_formats:
                    return {
                        "result": "success",
                        "file_type": file_type_hint
                    }
                else:
                    self.logger.warning("Подсказка типа '%s' не в списке поддерживаемых", file_type_hint)
            
            # 1. Try magic bytes (most reliable)
            guess = filetype.guess(str(file_path))
            if guess:
                detected_type = guess.extension
                
                if detected_type in self.supported_formats:
                    return {
                        "result": "success",
                        "file_type": detected_type
                    }
            
            # 2. Try Content-Type header
            if content_type:
                ext = self.mime_to_ext.get(content_type)
                if ext:
                    detected_type = ext
                    
                    if detected_type in self.supported_formats:
                        return {
                            "result": "success",
                            "file_type": detected_type
                        }
            
            # 3. Try file extension from path (fallback)
            ext = file_path.suffix.lower().lstrip('.')
            if ext:
                detected_type = ext
                
                if detected_type in self.supported_formats:
                    return {
                        "result": "success",
                        "file_type": detected_type
                    }
            
            # 4. Default to txt for unknown text files
            # This is a safe fallback for plain text content
            if detected_type is None:
                self.logger.warning("Тип файла не определён, по умолчанию 'txt'")
                return {
                    "result": "success",
                    "file_type": "txt"
                }
            
            # 5. For generic/unknown extensions (e.g. .bin from Google Drive), try content sniffing
            # Many servers save files as application/octet-stream without proper extension
            generic_extensions = ('bin', 'dat', 'data', '')
            if detected_type in generic_extensions or not ext:
                text_type = self._sniff_text_file(file_path)
                if text_type:
                    return {
                        "result": "success",
                        "file_type": text_type
                    }
            
            return {
                "result": "error",
                "error": {
                    "code": "UNSUPPORTED_FORMAT",
                    "message": f"Тип '{detected_type}' не поддерживается. Доступны: {', '.join(self.supported_formats)}"
                }
            }

        except Exception as e:
            self.logger.error("Ошибка определения типа файла: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Ошибка определения типа: {e}"
                }
            }
