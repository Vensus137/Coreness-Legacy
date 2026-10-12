# Чистая переустановка зависимостей: удалить .venv и кэш pip, создать .venv заново, установить только requirements.txt + PyInstaller.
# В конце при необходимости запускает сборку backend из этого же .venv (см. -Build).
# Запускать из корня проекта.

param(
    [switch]$Build  # после установки зависимостей запустить scripts\build-backend.ps1
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$VenvPath = Join-Path $ProjectRoot ".venv"

# 1. Удалить старый venv (весь мусор из окружения уйдёт)
if (Test-Path $VenvPath) {
    Write-Host "Удаление старого .venv..."
    Remove-Item -Recurse -Force $VenvPath
}

# 2. Очистить кэш pip
Write-Host "Очистка кэша pip..."
pip cache purge 2>$null; if (-not $?) { pip cache clear 2>$null }

# 3. Новый venv
Write-Host "Создание .venv..."
python -m venv $VenvPath

# 4. Установка в .venv (активация в этом процессе)
& (Join-Path $VenvPath "Scripts\Activate.ps1")
python -m pip install --upgrade pip --quiet
Write-Host "Установка зависимостей из requirements.txt..."
pip install -r requirements.txt --quiet
Write-Host "Установка PyInstaller для сборки..."
pip install pyinstaller -q

Write-Host ""
if ($Build) {
    Write-Host "Запуск сборки backend из .venv..."
    & (Join-Path $ProjectRoot "scripts\build-backend.ps1")
    $buildExit = $LASTEXITCODE
    if ($buildExit -eq 0 -and (Test-Path $VenvPath)) {
        Write-Host "Удаление .venv (после сборки не нужен)..."
        Remove-Item -Recurse -Force $VenvPath
    }
    exit $buildExit
} else {
    Write-Host "Готово. Окружение чистое. Сборка: .\scripts\build-backend.ps1 (идёт из .venv) или переустановка + сборка: .\scripts\clean-and-install-deps.ps1 -Build"
    Write-Host ""
}
