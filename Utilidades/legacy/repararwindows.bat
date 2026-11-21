@echo off
:: ==============================================================================
:: NOMBRE: RepararWindows.bat
:: DESCRIPCION: Lanzador con resolucion dinamica de rutas y elevacion UAC.
:: ==============================================================================
SETLOCAL ENABLEEXTENSIONS

:: Resolucion dinamica del directorio donde habita el archivo .bat
SET "SCRIPT_DIR=%~dp0"
SET "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
SET "LOCAL_SCRIPT=%SCRIPT_DIR%\RepararWindows.ps1"

:: Validacion de existencia local antes de solicitar elevacion
IF NOT EXIST "%LOCAL_SCRIPT%" (
    echo [ERROR] No se encontro el archivo RepararWindows.ps1 en: %SCRIPT_DIR%
    pause
    exit /b 1
)

:: Invocacion hacia PowerShell elevando privilegios a Administrador (RunAs)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoExit -NoProfile -ExecutionPolicy Bypass -File \"%LOCAL_SCRIPT%\"' -Verb RunAs"

ENDLOCAL
exit /b 0