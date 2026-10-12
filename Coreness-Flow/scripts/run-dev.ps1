# Запуск приложения в режиме разработки (без сборки).
# Из корня проекта: .\scripts\run-dev.ps1
# Запускает Vite + Electron; backend поднимается автоматически из main process.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "Coreness Flow — dev (Vite + Electron, backend стартует из Electron)"
Set-Location $FrontendDir
npm run electron:dev
