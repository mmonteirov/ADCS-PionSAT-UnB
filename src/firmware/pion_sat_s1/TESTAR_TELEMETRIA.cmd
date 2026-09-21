@echo off
title Teste de Telemetria - PION Sat
cd /d "C:\Users\diang\Documents\Codex\2026-08-26\pr\outputs\pion_sat_s1_firmware"
echo ============================================================
echo   PION Sat - teste ao vivo da telemetria (COM5 / 115200)
echo ============================================================
echo.
echo O teste dura 60 segundos e mostra uma linha por segundo.
echo Depois de aparecer a primeira linha, movimente e gire o satelite.
echo RPY, gyro e magnetometro devem mudar imediatamente.
echo Nao abra a Ground Station ou outro monitor serial ao mesmo tempo.
echo.
"C:\Users\diang\Documents\Codex\2026-08-26\pr\work\adcs_test_venv\Scripts\python.exe" tools\test_live_telemetry.py --port COM5 --seconds 60 --ground-station-root "C:\Users\diang\Documents\Codex\2026-08-26\pr\work\ADCS-PionSAT-UnB-20260918"
echo.
echo Pressione uma tecla para fechar.
pause >nul
