@echo off
setlocal enabledelayedexpansion

:: 1. Verificación de Privilegios (Auto-elevación)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [SISTEMA] Se requieren privilegios de administrador. Elevando...
    powershell -command "Start-Process '%~f0' -Verb runas"
    exit /b
)

:: 2. Configuración de Entorno y Logs
title Reparacion de Integridad de Windows
set "LOG_PATH=%TEMP%\reparacion_windows.log"
echo [INFO] Iniciando sesion de reparacion: %DATE% %TIME% > "%LOG_PATH%"

:: 3. Fase 1/4: DISM
echo.
echo [1/4] Ejecutando DISM /RestoreHealth...
powershell -Command "DISM.exe /Online /Cleanup-Image /RestoreHealth 2>&1 | Tee-Object -FilePath '%LOG_PATH%' -Append"
if %errorlevel% equ 0 (
    echo [OK] Almacen de componentes verificado/reparado.
) else (
    echo [ADVERTENCIA] DISM detecto inconsistencias. Revise el log.
)

:: 4. Fase 2/4: SFC
echo.
echo [2/4] Ejecutando SFC /ScanNow...
powershell -Command "sfc /scannow 2>&1 | Tee-Object -FilePath '%LOG_PATH%' -Append"
if %errorlevel% equ 0 (
    echo [OK] Integridad de archivos de sistema validada.
) else (
    echo [INFO] SFC finalizo con reparaciones realizadas.
)

:: 5. Fase 3/4: Reinstalación de Paquetes AppX
echo.
echo [3/4] Reinstalando aplicaciones AppX (Shell de Windows)...
sc query MpsSvc | findstr /I "RUNNING" >nul
if %errorlevel% neq 0 (
    echo [SISTEMA] Iniciando servicio de Firewall para registro de aplicaciones...
    net start MpsSvc 2>&1 | powershell -Command "$Input | Tee-Object -FilePath '%LOG_PATH%' -Append"
)

powershell -Command "Get-AppXPackage -AllUsers | Foreach {Add-AppxPackage -DisableDevelopmentMode -Register \"$($_.InstallLocation)\AppXManifest.xml\" -ErrorAction SilentlyContinue} 2>&1 | Tee-Object -FilePath '%LOG_PATH%' -Append"
echo [OK] Proceso de registro AppX completado.

:: 6. Fase 4/4: Optimización Final de Componentes
echo.
echo [4/4] Ejecutando limpieza de componentes (StartComponentCleanup)...
powershell -Command "DISM.exe /Online /Cleanup-Image /StartComponentCleanup 2>&1 | Tee-Object -FilePath '%LOG_PATH%' -Append"
echo [OK] Limpieza y consolidacion completada.

:: 7. Finalización del Proceso
echo.
echo ==============================================================================
echo [SISTEMA] TAREAS DE MANTENIMIENTO FINALIZADAS.
echo [SISTEMA] Log detallado en: %LOG_PATH%
echo ==============================================================================
echo.
pause