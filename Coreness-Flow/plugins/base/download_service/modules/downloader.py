"""Модуль загрузки файлов по HTTP (прямые ссылки, Google Drive, Google Docs/Sheets)."""

import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

import aiofiles
import aiohttp


class Downloader:
    """Загрузка файлов по URL: прямые ссылки, Google Drive, Google Docs/Sheets."""

    def __init__(self, logger, downloads_path: Path):
        self.logger = logger
        self.downloads_path = downloads_path

    def _convert_google_drive_url(self, url: str) -> str:
        """Преобразует ссылку Google Drive вида /file/d/ID/view в прямую загрузку."""
        # Pattern: https://drive.google.com/file/d/{FILE_ID}/view?usp=...
        match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url
    
    def _convert_github_url(self, url: str) -> Optional[str]:
        """Преобразует GitHub blob-URL в raw: получаем содержимое файла вместо HTML."""
        # Match: https://github.com/{owner}/{repo}/blob/{branch}/{path}
        match = re.search(
            r'^https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$',
            url.strip(),
            re.IGNORECASE
        )
        if match:
            owner, repo, branch, path = match.groups()
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        return None

    def _convert_google_docs_url(self, url: str) -> tuple[str, Optional[str]]:
        """Преобразует URL Google Docs/Sheets в URL экспорта. Возвращает (url, расширение)."""
        # Google Docs: https://docs.google.com/document/d/{DOC_ID}/edit
        doc_match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
        if doc_match:
            doc_id = doc_match.group(1)
            return f"https://docs.google.com/document/d/{doc_id}/export?format=txt", "txt"
        
        # Google Sheets: export as CSV (format=html is not supported by public export, returns 400)
        sheet_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
        if sheet_match:
            sheet_id = sheet_match.group(1)
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0", "csv"
        
        return url, None
    
    def _normalize_url(self, url: str) -> tuple[str, Optional[str]]:
        """Нормализует URL под разные сервисы. Возвращает (url, опциональное расширение)."""
        # GitHub blob URL -> raw file URL (otherwise we get HTML page instead of file content)
        github_raw = self._convert_github_url(url)
        if github_raw:
            return github_raw, None

        # Google Drive
        if 'drive.google.com/file' in url:
            return self._convert_google_drive_url(url), None
        
        # Google Docs/Sheets
        if 'docs.google.com' in url:
            return self._convert_google_docs_url(url)
        
        return url, None
    
    def _parse_content_disposition_filename(self, content_disposition: Optional[str]) -> Optional[str]:
        """Извлекает имя файла из заголовка Content-Disposition."""
        if not content_disposition:
            return None
        match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', content_disposition, re.I)
        if match:
            return unquote(match.group(1).strip()).strip('"\'')
        return None

    def _generate_filename(self, url: str, content_type: Optional[str] = None,
                           content_disposition: Optional[str] = None) -> str:
        """Формирует уникальное имя файла: {timestamp}_{url_hash}.{ext}."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        url_hash = hashlib.md5(url.encode()).hexdigest()[:6]
        
        # Detect extension from Content-Disposition, URL or Content-Type
        ext = 'bin'  # default
        
        # Try Content-Disposition first (Google Drive and many CDNs send actual filename)
        disp_filename = self._parse_content_disposition_filename(content_disposition)
        if disp_filename:
            disp_ext = Path(disp_filename).suffix.lstrip('.').lower()
            if disp_ext in ('pdf', 'docx', 'txt', 'md', 'html', 'csv'):
                ext = disp_ext
        
        # Try to get extension from URL
        if ext == 'bin':
            parsed_url = urlparse(url)
            path = parsed_url.path
            if path:
                url_ext = Path(path).suffix.lstrip('.').lower()
                if url_ext in ('pdf', 'docx', 'txt', 'md', 'html', 'csv'):
                    ext = url_ext
        
        # Try to get extension from Content-Type
        if ext == 'bin' and content_type:
            content_type_map = {
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'text/plain': 'txt',
                'text/markdown': 'md',
                'text/html': 'html',
                'text/csv': 'csv',
                'application/csv': 'csv'
            }
            if content_type in content_type_map:
                ext = content_type_map[content_type]
        
        return f"{timestamp}_{url_hash}.{ext}"
    
    async def _check_file_size(self, session: aiohttp.ClientSession, url: str, max_size_mb: int) -> Dict[str, Any]:
        """Проверяет размер файла через HEAD. Возвращает dict с result или error."""
        try:
            async with session.head(url, allow_redirects=True) as response:
                if response.status != 200:
                    self.logger.warning("HEAD вернул %s, проверка размера пропущена", response.status)
                    return {"result": "success"}  # Skip check if HEAD not supported
                
                content_length = response.headers.get('Content-Length')
                if content_length:
                    size_bytes = int(content_length)
                    size_mb = size_bytes / (1024 * 1024)
                    
                    if size_mb > max_size_mb:
                        return {
                            "result": "error",
                            "error": {
                                "code": "FILE_TOO_LARGE",
                                "message": f"Размер файла ({size_mb:.2f} МБ) превышает лимит ({max_size_mb} МБ)"
                            }
                        }
                
                return {"result": "success"}
        
        except Exception as e:
            self.logger.warning("Не удалось проверить размер файла: %s", e)
            return {"result": "success"}

    async def download_file(self, url: str, max_size_mb: int, timeout_seconds: int) -> Dict[str, Any]:
        """Скачивает файл по URL. Возвращает dict с file_path, file_size, content_type, download_timestamp или error."""
        try:
            normalized_url, detected_type = self._normalize_url(url)
            self.downloads_path.mkdir(parents=True, exist_ok=True)
            
            # Configure timeout
            timeout = aiohttp.ClientTimeout(total=timeout_seconds)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Check file size via HEAD request
                size_check = await self._check_file_size(session, normalized_url, max_size_mb)
                if size_check.get('result') == 'error':
                    return size_check
                
                # Download file
                async with session.get(normalized_url) as response:
                    if response.status != 200:
                        return {
                            "result": "error",
                            "error": {
                                "code": "DOWNLOAD_FAILED",
                                "message": f"HTTP {response.status}: не удалось загрузить файл по {url}"
                            }
                        }
                    
                    # Get content type and content disposition
                    content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
                    content_disposition = response.headers.get('Content-Disposition')
                    
                    filename = self._generate_filename(url, content_type, content_disposition)
                    file_path = self.downloads_path / filename
                    
                    # Download and save file
                    content = await response.read()
                    file_size = len(content)
                    
                    # Final size check (after download)
                    size_mb = file_size / (1024 * 1024)
                    if size_mb > max_size_mb:
                        return {
                            "result": "error",
                            "error": {
                                "code": "FILE_TOO_LARGE",
                                "message": f"Размер загруженного файла ({size_mb:.2f} МБ) превышает лимит ({max_size_mb} МБ)"
                            }
                        }
                    
                    # Save to file
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    
                    self.logger.info("Файл загружен: %s (%s байт)", file_path, file_size)
                    
                    return {
                        "result": "success",
                        "file_path": file_path,
                        "file_size": file_size,
                        "content_type": content_type,
                        "download_timestamp": datetime.now().isoformat()
                    }
        
        except asyncio.TimeoutError:
            raise

        except aiohttp.ClientError as e:
            self.logger.error("Ошибка HTTP при загрузке: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "DOWNLOAD_FAILED",
                    "message": f"Сетевая ошибка: {e}"
                }
            }

        except Exception as e:
            self.logger.error("Ошибка загрузки файла: %s", e)
            return {
                "result": "error",
                "error": {
                    "code": "DOWNLOAD_FAILED",
                    "message": f"Ошибка загрузки: {e}"
                }
            }
