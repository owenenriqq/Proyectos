@echo off
:: Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~s0' -Verb RunAs"
    exit
)

echo Generando informe de bateria...
setlocal
set REPORT_PATH=%TEMP%\battery-report.html
powercfg /batteryreport /output "%REPORT_PATH%"
echo Informe generado en: %REPORT_PATH%
echo Abriendo informe...
start "" "%REPORT_PATH%"
endlocal
pause
