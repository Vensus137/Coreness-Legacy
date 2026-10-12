"""Утилиты для тестов."""
import os
from pathlib import Path


def find_project_root(start_path: Path = None) -> Path:
    """Надёжно определяет корень проекта."""
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    if start_path is None:
        start_path = Path(__file__)
    
    current = start_path.resolve()
    
    if current.is_file():
        current = current.parent
    
    while current != current.parent:
        if (current / "run_backend.py").exists() and \
           (current / "plugins").exists() and \
           (current / "app").exists():
            return current
        current = current.parent
    
    if start_path.name == "tests" or "tests" in start_path.parts:
        return start_path.parent if start_path.is_dir() else start_path.parent.parent
    
    return start_path.parent if start_path.is_file() else start_path

