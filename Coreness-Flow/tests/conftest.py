"""
Base fixtures for tests. Plugin tests live in plugins/core/<plugin>/tests/ and use local conftest.
"""
import asyncio
import os
from pathlib import Path

import pytest

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def _find_project_root(start_path: Path) -> Path:
    """Determine project root by key files."""
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (current / "run_backend.py").exists() and (current / "plugins").exists() and (current / "app").exists():
            return current
        current = current.parent
    return start_path.parent if start_path.is_file() else start_path


PROJECT_ROOT = _find_project_root(Path(__file__))


@pytest.fixture(scope="session")
def event_loop():
    """Event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Project root path."""
    return PROJECT_ROOT
