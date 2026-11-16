@echo off
setlocal
pushd "%~dp0"

:: Verificar si la sesion cuenta con privilegios de Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando elevacion de privilegios de Administrador...
    powershell.exe -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    popd
    exit /b
)

:: Ejecutar el script principal con ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\Invoke-M365Sanitizer.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] La ejecucion finalizo con codigo de error %errorlevel%.
    pause
)

popd
endlocal
