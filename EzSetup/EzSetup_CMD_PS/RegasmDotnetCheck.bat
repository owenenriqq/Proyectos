@echo off
:: Verificar si se ejecuta como administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    :: Elevar el proceso sin mostrar la ventana de notificación
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)


::======================================================================================================================================================================
::======================================================================================================================================================================


:: Configuracion de ventana
title Regasm_DotNet_Check
mode con: cols=93 lines=13
cls


::======================================================================================================================================================================
::======================================================================================================================================================================


:: Verificar si .NET Framework 3.5 esta instalado
reg query "HKLM\SOFTWARE\Microsoft\NET Framework Setup\NDP\v3.5" /v Install >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] .NET Framework 3.5 se encuentra instalado correctamente.
) else (
    echo [ADVERTENCIA] .NET Framework 3.5 NO se encuentra instalado.
)

:: Ejecutar registro de la DLL con salida visible
set "frameworkDir=%SystemRoot%\Microsoft.NET\Framework\v4.0.30319"
cd /d "%frameworkDir%"
echo.
echo %frameworkDir%^>RegAsm.exe WinSCPnet.dll /codebase /tlb
RegAsm.exe WinSCPnet.dll /codebase /tlb
echo.


::======================================================================================================================================================================
::======================================================================================================================================================================


setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[CERRANDO] Esta ventana se cerrara en %%i segundos...
    timeout /t 1 >nul
)
exit /b
