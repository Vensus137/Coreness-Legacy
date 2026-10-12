# Остановка процессов dev: backend (порт 29773) и Vite (порт 29774).
# Запускать из корня, если закрыли терминал и приложение осталось висеть.

$ErrorActionPreference = "Stop"

function Stop-ByPort($port) {
  $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
  if ($conn) {
    $conn | ForEach-Object {
      $procId = $_.OwningProcess
      $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
      if ($proc) {
        Write-Host "Останавливаю PID $procId ($($proc.ProcessName)) на порту $port"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      }
    }
  }
}

Write-Host "Остановка dev (порты 29773, 29774)..."
Stop-ByPort 29773
Stop-ByPort 29774
Write-Host "Готово."
