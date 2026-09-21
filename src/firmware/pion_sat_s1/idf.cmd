@echo off
setlocal

where idf.py >nul 2>nul
if errorlevel 1 (
    echo ERRO: idf.py nao esta no PATH.
    echo Abra um terminal ESP-IDF ou execute export.bat da instalacao do ESP-IDF.
    exit /b 1
)

idf.py %*
exit /b %errorlevel%
