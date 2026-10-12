# Сборка Python backend (PyInstaller). Запускать из корня проекта.
# Сборка всегда идёт из .venv (только его зависимости попадут в бандл). Без .venv — сначала запустите scripts\clean-and-install-deps.ps1.
# Результат: build/backend/coreness-backend.exe + DLL и зависимости в той же папке.
# Используется --onedir (не --onefile), чтобы не было распаковки при запуске и ошибок
# вида "Failed to extract VCRUNTIME140.dll: Permission denied" при старте из Electron.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$VenvPath = Join-Path $ProjectRoot ".venv"
$PyinstallerExe = Join-Path $VenvPath "Scripts\pyinstaller.exe"
if (-not (Test-Path $PyinstallerExe)) {
    Write-Error ".venv не найден или в нём нет PyInstaller. Сначала выполните: .\scripts\clean-and-install-deps.ps1"
}

$OutDir = Join-Path $ProjectRoot "build\backend"
$SpecPath = Join-Path $ProjectRoot "build\pyinstaller"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path $SpecPath | Out-Null

# Сборка по spec из .venv: в бандл попадут только зависимости из requirements.txt (см. scripts/coreness-backend.spec)
Write-Host "Сборка backend из .venv (режим onedir)..."
& $PyinstallerExe (Join-Path $ProjectRoot "scripts\coreness-backend.spec") `
  --distpath $OutDir `
  --workpath $SpecPath `
  --noconfirm

# --onedir кладёт exe в build/backend/coreness-backend/; electron-builder ожидает exe и _internal в build/backend/
if (Test-Path (Join-Path $OutDir "coreness-backend\coreness-backend.exe")) {
  # Сначала удалить старые артефакты в $OutDir (от прошлой сборки), иначе Move-Item падает с "file already exists"
  Get-ChildItem $OutDir | Where-Object { $_.Name -ne "coreness-backend" } | Remove-Item -Recurse -Force
  Get-ChildItem (Join-Path $OutDir "coreness-backend") | Move-Item -Destination $OutDir -Force
  Remove-Item (Join-Path $OutDir "coreness-backend") -Force -ErrorAction SilentlyContinue
}
Write-Host "Готово: $OutDir\coreness-backend.exe"
