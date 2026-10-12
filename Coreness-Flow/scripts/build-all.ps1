# Полная сборка: backend (PyInstaller из .venv) + frontend (Electron Builder). Запускать из корня проекта.
# Результат: build/electron/ (распакованное приложение и установщик NSIS)
# Backend собирается через clean-and-install-deps -Build (создаётся .venv, сборка, затем .venv удаляется).

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$VenvPath = Join-Path $ProjectRoot ".venv"

Write-Host "=== 1. Сборка Python backend ==="
& (Join-Path $ProjectRoot "scripts\clean-and-install-deps.ps1") -Build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (Test-Path $VenvPath) {
    Write-Host "Удаление .venv (для сборки больше не нужен)..."
    Remove-Item -Recurse -Force $VenvPath
}

Write-Host "=== 2. Сборка Electron (frontend + установщик) ==="
$ModelsDir = Join-Path $ProjectRoot "models"
if (-not (Test-Path $ModelsDir)) {
  New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null
  Write-Host "Создана пустая папка models/ (для vector_store скачайте модель: python dev/scripts/download_bge_m3_onnx.py)"
}
Set-Location (Join-Path $ProjectRoot "frontend")
npm run electron:build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Готово. Распакованное приложение: build\electron\win-unpacked\CorenessFlow.exe"
Write-Host "Установщик: build\electron\"
Set-Location $ProjectRoot
