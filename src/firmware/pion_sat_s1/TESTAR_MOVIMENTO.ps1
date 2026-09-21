$Host.UI.RawUI.WindowTitle = "Teste de movimento real - PION Sat"
$firmwareRoot = "C:\Users\diang\Documents\Codex\2026-08-26\pr\outputs\pion_sat_s1_firmware"
$pythonExe = "C:\Users\diang\Documents\Codex\2026-08-26\pr\work\adcs_test_venv\Scripts\python.exe"
$groundStation = "C:\Users\diang\Documents\Codex\2026-08-26\pr\work\ADCS-PionSAT-UnB-20260918"
$resultLog = Join-Path $firmwareRoot "tools\motion_test_result.txt"

Set-Location $firmwareRoot
Clear-Host
Write-Host "PION Sat - teste da IMU fisica" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Deixe o satelite PARADO enquanto aparece 'aguardando pacotes'." -ForegroundColor Yellow
Write-Host "2. Quando surgir a primeira linha com RPY, gire e incline o satelite." -ForegroundColor Green
Write-Host "3. Observe RPY, gyro e magnetometro mudando em tempo real." -ForegroundColor Green
Write-Host ""

& $pythonExe tools\test_live_telemetry.py --port COM5 --seconds 45 --ground-station-root $groundStation 2>&1 |
    Tee-Object -FilePath $resultLog

Write-Host ""
Write-Host "Teste encerrado. Esta janela pode ser fechada." -ForegroundColor Cyan
Read-Host "Pressione Enter para fechar"
