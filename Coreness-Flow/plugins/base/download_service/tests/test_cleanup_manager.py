"""
Tests for CleanupManager module
"""
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from modules.cleanup_manager import CleanupManager


class TestCleanupManager:
    """Test CleanupManager functionality"""
    
    def test_cleanup_file(self, logger, tmp_path):
        """Test immediate file cleanup"""
        manager = CleanupManager(
            logger=logger,
            downloads_path=tmp_path,
            max_age_seconds=86400,
            enabled=False,
            cleanup_interval_seconds=3600,
        )

        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        assert test_file.exists()
        
        # Cleanup
        result = manager.cleanup_file(test_file)
        
        assert result is True
        assert not test_file.exists()
    
    def test_cleanup_nonexistent_file(self, logger, tmp_path):
        """Test cleanup of nonexistent file"""
        manager = CleanupManager(
            logger=logger,
            downloads_path=tmp_path,
            max_age_seconds=86400,
            enabled=False,
            cleanup_interval_seconds=3600,
        )

        nonexistent = tmp_path / "nonexistent.txt"
        result = manager.cleanup_file(nonexistent)
        
        assert result is False


@pytest.mark.asyncio
class TestCleanupManagerAsync:
    """Test async CleanupManager functionality"""
    
    async def test_cleanup_old_files(self, logger, tmp_path):
        """Test cleanup of old files"""
        manager = CleanupManager(
            logger=logger,
            downloads_path=tmp_path,
            max_age_seconds=3600,
            enabled=False,
            cleanup_interval_seconds=86400,
        )

        old_file = tmp_path / "old.txt"
        old_file.write_text("old")
        old_time = datetime.now() - timedelta(hours=2)
        old_timestamp = old_time.timestamp()
        old_file.touch()
        import os
        os.utime(old_file, (old_timestamp, old_timestamp))

        new_file = tmp_path / "new.txt"
        new_file.write_text("new")

        deleted_count = await manager.cleanup_old_files()

        assert deleted_count == 1
        assert not old_file.exists()
        assert new_file.exists()
