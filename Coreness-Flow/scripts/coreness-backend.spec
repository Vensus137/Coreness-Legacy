# -*- mode: python ; coding: utf-8 -*-
# Универсальная сборка backend: точки входа плагинов подключаются к анализу,
# чтобы PyInstaller автоматически подтянул все их зависимости (без хардкода hidden-import).
# Запуск: из корня проекта (build-backend.ps1 делает Set-Location $ProjectRoot).

import json
import os
from pathlib import Path

block_cipher = None

# Корень проекта (spec запускается при сборке из корня)
_project_root = Path(".").resolve()


def _discover_plugin_entry_scripts():
    """Те же правила, что в app.runtime.container: каталоги с config.json, главный модуль — name из config или первый .py."""
    scripts = []
    plugins_root = _project_root / "plugins"
    if not plugins_root.exists():
        return scripts
    for root, _dirs, _files in os.walk(plugins_root):
        pdir = Path(root)
        if not (pdir / "config.json").exists():
            continue
        try:
            with open(pdir / "config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {}
        meta = config.get("metadata") or {}
        name = meta.get("name") or config.get("name")
        plugin_name = name.strip() if isinstance(name, str) else pdir.name
        candidates = [pdir / f"{plugin_name}.py"]
        if not candidates[0].exists():
            candidates = sorted(pdir.glob("*.py"), key=lambda p: p.name)
            candidates = [p for p in candidates if not p.name.startswith("__")]
        if candidates:
            scripts.append(str(candidates[0].resolve()))
    return scripts


# Все скрипты для анализа зависимостей: основной backend + точки входа плагинов
_main_script = str((_project_root / "run_backend.py").resolve())
_plugin_scripts = _discover_plugin_entry_scripts()
_scripts = [_main_script] + _plugin_scripts

# Скрытые импорты: зависимости плагинов, которые PyInstaller может не обнаружить при статическом анализе
# (особенно для динамически загружаемых модулей)
_hidden_imports = [
    "sqlite3",  # stdlib, иногда не подхватывается
    "websockets",
    "yaml",
    "aiofiles",
    "aiohttp",
    "numpy",
    "croniter",
    "filetype",
    "chardet",
    "fitz",  # PyMuPDF
    "pandas",
    "bs4",  # BeautifulSoup
    "docx",  # python-docx
    "dateutil",
    "dateutil.relativedelta",
    "qdrant_client",
    "onnxruntime",
    "psutil",
    "openai",
    "markdown",
    "pygments",
    "transformers",  # только AutoTokenizer для BGE-M3; torch не используем
]

# Только тяжёлые/ненужные пакеты — исключаем вручную.
# torch — тянется из transformers; используем только ONNX + AutoTokenizer.
# scipy, sklearn — опциональные зависимости pandas/transformers, в коде не импортируются.
# pyarrow — тянется pandas; read_html использует lxml, не pyarrow (~77 MB).
# Pythonwin — GUI (MFC), для headless backend не нужен (~6.5 MB).
# psycopg2, asyncpg — драйверы PostgreSQL; исключить, если БД не используется (~3 MB).
_excludes = [
    "torch",
    "torch.*",
    "scipy",
    "scipy.*",
    "sklearn",
    "sklearn.*",
    "pyarrow",
    "pyarrow.*",
    "Pythonwin",
    "Pythonwin.*",
    "psycopg2",
    "psycopg2.*",
    "asyncpg",
    "asyncpg.*",
]

a = Analysis(
    _scripts,
    pathex=[str(_project_root)],
    binaries=None,
    datas=None,
    hiddenimports=_hidden_imports,
    hookspath=None,
    hooksconfig=None,
    runtime_hooks=None,
    excludes=_excludes,
    noarchive=False,
    optimize=0,
)

# Используем только CPU (embedding_manager: CPUExecutionProvider). Исключаем из бандла провайдеры GPU (~298 MB CUDA, ~0.8 MB TensorRT).
_skip_gpu = ("cuda", "tensorrt")
a.binaries = [x for x in a.binaries if not any(s in x[0].lower() or s in str(x[1]).lower() for s in _skip_gpu)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="coreness-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="coreness-backend",
)
