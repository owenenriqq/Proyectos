@echo off
:: Verificar si ya está elevado
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb runAs"
    exit /b
)


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================


:: Configuracion de ventana
title EzSetup
mode con: cols=80 lines=38
cls


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================




:MENU
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    PROGRAMAS - CARACTERISTICAS:'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] EIDICO'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [2] TECNICA'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [3] IT'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [4] Microsoft Office 365 - 2021       ^|      ' -NoNewline; Write-Host 'MAS' -ForegroundColor DarkCyan; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [5] Adobe Master Collection - 2022'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [6] Credenciales de Windows'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Salir'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,5,6,0]:' -ForegroundColor Green -NoNewline"

choice /C:1234560 /N
set _opt=%errorlevel%

if %_opt%==1 goto SUBMENU_EIDICO
if %_opt%==2 goto SUBMENU_TECNICA
if %_opt%==3 goto SUBMENU_IT
if %_opt%==4 goto SUBMENU_O365
if %_opt%==5 goto ADOBE
if %_opt%==6 goto CREDENCIALES
if %_opt%==7 exit
goto MENU




::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================



:SUBMENU_EIDICO
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    PROGRAMAS EIDICO:'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] .NET Framework 3.5'; ^
 Write-Host ''; ^
 Write-Host '                [2] FortiClient'; ^
 Write-Host ''; ^
 Write-Host '                [3] AWS VPN Client'; ^
 Write-Host ''; ^
 Write-Host '                [4] Sistema contable'; ^
 Write-Host ''; ^
 Write-Host '                [5] WinSCP'; ^
 Write-Host ''; ^
 Write-Host '                [6] OpenVPN'; ^
 Write-Host ''; ^
 Write-Host '                [7] Nitro PDF'; ^
 Write-Host ''; ^
 Write-Host '                [8] Fondos Eidico'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,5,6,7,8,0]:' -ForegroundColor Green -NoNewline"

choice /C:123456780 /N
set _eidico=%errorlevel%

if %_eidico%==1 goto .NET
if %_eidico%==2 goto SUBMENU_FORTICLIENT
if %_eidico%==3 goto SUBMENU_AWSVPNCLIENT
if %_eidico%==4 goto SUBMENU_SISTEMA
if %_eidico%==5 goto SUBMENU_WINSCP
if %_eidico%==6 goto SUBMENU_OPENVPN
if %_eidico%==7 goto SUBMENU_NITROPDF
if %_eidico%==8 goto FONDOS_EIDICO
if %_eidico%==9 goto MENU
goto SUBMENU_EIDICO



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================


:.NET
cls
echo [INFO] Abriendo caracteristicas de Windows.
start optionalfeatures
timeout /t 3 >nul
goto SUBMENU_EIDICO


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:SUBMENU_FORTICLIENT
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    FortiClient'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar FortiClient'; ^
 Write-Host ''; ^
 Write-Host '                [2] Descargar FortiClient'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,0]:' -ForegroundColor Green -NoNewline"

choice /C:120 /N
set "_forti=%errorlevel%"

if %_forti%==1 goto INSTALAR_FORTICLIENT
if %_forti%==2 goto DESCARGAR_FORTICLIENT
if %_forti%==3 goto SUBMENU_EIDICO
goto SUBMENU_FORTICLIENT


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_FORTICLIENT
cls
echo [INFO] Ejecutando instalador de FortiClient.
start "" "\\172.30.0.13\areas\0-IT\FortiClient_x64.zip"
timeout /t 3 >nul
goto SUBMENU_FORTICLIENT

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:DESCARGAR_FORTICLIENT
cls
echo [INFO] Iniciando descarga de FortiClient.
set "scriptPath=%~dp0"
start powershell -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%DescargarFortiClient.ps1'"0
timeout /t 3 >nul
goto SUBMENU_FORTICLIENT

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:SUBMENU_AWSVPNCLIENT
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    AWS VPN Client'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar AWS VPN Client'; ^
 Write-Host ''; ^
 Write-Host '                [2] Descargar AWS VPN Client'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,0]:' -ForegroundColor Green -NoNewline"

choice /C:120 /N
set "_aws=%errorlevel%"

if %_aws%==1 goto INSTALAR_AWSVPNCLIENT
if %_aws%==2 goto DESCARGAR_AWSVPNCLIENT
if %_aws%==3 goto MENU
goto SUBMENU_AWSVPNCLIENT


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_AWSVPNCLIENT
cls
echo [INFO] Ejecutando instalador de AWS VPN Client.
start "" msiexec /i "\\172.30.0.13\areas\0-IT\AWS_VPN_Client.msi"
timeout /t 3 >nul
goto SUBMENU_AWSVPNCLIENT

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:DESCARGAR_AWSVPNCLIENT
cls
echo [INFO] Iniciando descarga de AWS VPN Client.
set "scriptPath=%~dp0"
start powershell -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%DescargarAWSVPNClient.ps1'"
timeout /t 3 >nul
goto SUBMENU_AWSVPNCLIENT

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:SUBMENU_SISTEMA
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    Sistema contable'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar Sistema contable'; ^
 Write-Host ''; ^
 Write-Host '                [2] Descargar Sistema contable'; ^
 Write-Host ''; ^
 Write-Host '                [3] Corregir campo =Iniciar en='; ^
 Write-Host ''; ^
 Write-Host '                [4] Asignar permisos a carpeta Sol Sistemas'; ^
 Write-Host ''; ^
 Write-Host '                [5] Reemplazar script de inicio'; ^
 Write-Host ''; ^
 Write-Host '                [6] Copiar ejecutable en carpeta EIDICO'; ^
 Write-Host ''; ^
 Write-Host '                [7] Ejecutar opciones ' -NoNewline; Write-Host '3,4,5,6' -ForegroundColor DarkCyan; ^
 Write-Host ''; ^
 Write-Host '                [8] Extraer Produccion.zip en carpeta EIDICO'; ^
 Write-Host ''; ^
 Write-Host '                [9] Credenciales de windows'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,5,6,7,8,9,0]:' -ForegroundColor Green -NoNewline"

choice /C:1234567890 /N
set "_sistema=%errorlevel%"

if %_sistema%==1 goto INSTALAR_SISTEMA
if %_sistema%==2 goto DESCARGAR_SISTEMA
if %_sistema%==3 goto INICIAR_EN
if %_sistema%==4 goto PERMISOS_SOLSISTEMAS
if %_sistema%==5 goto COPIAR_VBS
if %_sistema%==6 goto COPIAR_EJECUTABLE
if %_sistema%==7 goto ALL_SISTEMA
if %_sistema%==8 goto PRODUCCION
if %_sistema%==9 goto CREDENCIALES_FOX
if %_sistema%==10 goto SUBMENU_EIDICO
goto SUBMENU_SISTEMA


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_SISTEMA
cls
echo [INFO] Ejecutando instalador Eidico.
start "" "\\172.30.0.13\areas\0-IT\Instalar_Fox_EIDICO\Instalar_Fox.exe"
timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:DESCARGAR_SISTEMA
cls
echo [INFO] Iniciando descarga de Eidico.
set "scriptPath=%~dp0"
start powershell -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=75 lines=5; & '%scriptPath%DescargarSistemaContable.ps1'"
timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:INICIAR_EN
cls
echo [INFO] Corrigiendo campo "Iniciar en" del acceso directo Eidico.
set "lnk=%USERPROFILE%\Desktop\Eidico.lnk"
set "workdir=C:\Program Files (x86)\Sol Sistemas\EIDICO\"
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%lnk%'); $s.WorkingDirectory='%workdir%'; $s.Save()" >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo actualizar el acceso directo.
) else (
    echo [OK] Campo 'Iniciar en' actualizado correctamente.
)
timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:PERMISOS_SOLSISTEMAS
cls
echo [INFO] Asignando permisos de usuario en Sol Sistemas.
set "scriptPath=%~dp0"
start powershell.exe -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%PermisosSolSistemas.ps1'"
timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:COPIAR_VBS
cls
echo [INFO] Copiando archivo EIDICO.vbs en carpeta EIDICO.

set "source=\\172.30.0.13\areas\0-IT\EIDICO.vbs"
set "dest=C:\Program Files (x86)\Sol Sistemas\EIDICO\"

copy /Y "%source%" "%dest%" >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo copiar el archivo.
) else (
    echo [OK] Archivo copiado correctamente.
)

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:COPIAR_EJECUTABLE
cls
echo [INFO] Copiando EidicoPrueba.EXE en carpeta EIDICO.

set "scriptPath=%~dp0"
start powershell -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%CopiarEidicoPrueba.ps1'"

timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:ALL_SISTEMA
cls
call :INICIAR_EN_ONLY
call :PERMISOS_SOLSISTEMAS_ONLY
call :COPIAR_VBS_ONLY
call :COPIAR_EJECUTABLE_ONLY
echo [OK] Todas las opciones fueron ejecutadas.
timeout /t 3 >nul
goto SUBMENU_SISTEMA

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:INICIAR_EN_ONLY
echo [INFO] Corrigiendo campo "Iniciar en" del acceso directo Eidico.lnk.
set "lnk=%USERPROFILE%\Desktop\Eidico.lnk"
set "workdir=C:\Program Files (x86)\Sol Sistemas\EIDICO\"
powershell -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%lnk%'); $s.WorkingDirectory='%workdir%'; $s.Save()" >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo actualizar el acceso directo.
) else (
    echo [OK] Campo 'Iniciar en' actualizado correctamente.
)
timeout /t 3 >nul
exit /b

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:PERMISOS_SOLSISTEMAS_ONLY
cls
echo [INFO] Asignando permisos via PowerShell.
set "scriptPath=%~dp0"
start powershell.exe -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%PermisosSolSistemas.ps1'"
timeout /t 3 >nul
exit /b

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:COPIAR_VBS_ONLY
cls
echo [INFO] Copiando archivo EIDICO.vbs en carpeta EIDICO.

set "source=\\172.30.0.13\areas\0-IT\EIDICO.vbs"
set "dest=C:\Program Files (x86)\Sol Sistemas\EIDICO\"

copy /Y "%source%" "%dest%" >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] No se pudo copiar el archivo.
) else (
    echo [OK] Archivo copiado correctamente.
)

timeout /t 3 >nul
exit /b

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:COPIAR_EJECUTABLE_ONLY
cls
echo [INFO] Copiando EidicoPrueba.EXE en carpeta EIDICO.

set "scriptPath=%~dp0"
start powershell -NoExit -ExecutionPolicy Bypass -Command "mode con: cols=70 lines=5; & '%scriptPath%CopiarEidicoPrueba.ps1'"

)

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_SISTEMA

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:PRODUCCION
cls
echo [INFO] Extrayendo archivos de Produccion.zip en EIDICO.

set "zip=\\172.30.0.13\areas\0-IT\Produccion.zip"
set "dest=C:\Program Files (x86)\Sol Sistemas\EIDICO"

powershell -Command ^
"Try { ^
    Expand-Archive -Path '%zip%' -DestinationPath '%dest%' -Force; ^
    exit 0 ^
} Catch { ^
    exit 1 ^
}"

if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron extraer los archivos de Produccion.zip en EIDICO.
) else (
    echo [OK] Se extrajeron los archivos correctamente.
)

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:CREDENCIALES_FOX
cls
echo [INFO] Ejecutando Credenciales de Fox.bat.
set "scriptPath=%~dp0"
start "" cmd /c ""%scriptPath%Credenciales de Fox.bat""

:: Cuenta regresiva (5 segundos) antes de volver al submenu
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_SISTEMA

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:SUBMENU_WINSCP
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    WinSCP'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar WinSCP'; ^
 Write-Host ''; ^
 Write-Host '                [2] Copiar WinSCPnet y WINSCP a carpeta de .NET'; ^
 Write-Host ''; ^
 Write-Host '                [3] Ejecutar RegAsm con /codebase /tlb'; ^
 Write-Host ''; ^
 Write-Host '                [4] Ejecutar opciones 2,3' -ForegroundColor DarkCyan; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,0]:' -ForegroundColor Green -NoNewline"

choice /C:12340 /N
set "_scp=%errorlevel%"

if %_scp%==1 goto INSTALAR_WINSCP
if %_scp%==2 goto COPIAR_WINSCP
if %_scp%==3 goto REGASM_WINSCP
if %_scp%==4 goto ALL_WINSCP
if %_scp%==5 goto SUBMENU_EIDICO
goto SUBMENU_WINSCP


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_WINSCP
cls
echo [INFO] Ejecutando instalador de WinSCP.
start "" "\\172.30.0.13\areas\0-IT\PMC Instalador WinSCP\WinSCP-5.13.3-Setup.exe"
timeout /t 3 >nul
goto SUBMENU_WINSCP

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:COPIAR_WINSCP
cls
echo [INFO] Copiando archivos en carpeta v4.0.30319.
set "sourceDir=\\172.30.0.13\areas\0-IT\PMC Instalador WinSCP"
set "targetDir=C:\Windows\Microsoft.NET\Framework\v4.0.30319\"
copy /Y "%sourceDir%\WinSCPnet.dll" "%targetDir%" >nul 2>&1
copy /Y "%sourceDir%\WINSCP.exe" "%targetDir%" >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron copiar los archivos.
) else (
    echo [OK] Archivos copiados correctamente.
)
:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_WINSCP

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:REGASM_WINSCP
cls
echo [INFO] Ejecutando Registro de DLL con RegAsm.bat.
set "scriptPath=%~dp0"
start "" cmd /c ""%scriptPath%RegasmDotnetCheck.bat""

:: Cuenta regresiva (5 segundos) antes de volver al submenu
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_WINSCP

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:ALL_WINSCP
cls
call :COPIAR_WINSCP_ONLY
call :REGASM_WINSCP_ONLY
echo [OK] Archivos copiados y DLL registrada.
timeout /t 3 >nul
goto SUBMENU_WINSCP

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:COPIAR_WINSCP_ONLY
echo [INFO] Copiando archivos en carpeta v4.0.30319...
set "sourceDir=\\172.30.0.13\areas\0-IT\PMC Instalador WinSCP"
set "targetDir=C:\Windows\Microsoft.NET\Framework\v4.0.30319\"
copy /Y "%sourceDir%\WinSCPnet.dll" "%targetDir%" >nul 2>&1
copy /Y "%sourceDir%\WINSCP.exe" "%targetDir%" >nul 2>&1
exit /b

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:REGASM_WINSCP_ONLY
cls
echo [INFO] Ejecutando Registro de DLL con RegAsm.bat.
set "scriptPath=%~dp0"
start "" cmd /c ""%scriptPath%RegasmDotnetCheck.bat""

:: Cuenta regresiva (5 segundos) antes de volver al submenu
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_WINSCP

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======


:SUBMENU_OPENVPN
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    OpenVPN'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar OpenVPN'; ^
 Write-Host ''; ^
 Write-Host '                [2] Copiar archivos a carpeta config'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,0]:' -ForegroundColor Green -NoNewline"

choice /C:120 /N
set "_openvpn=%errorlevel%"

if %_openvpn%==1 goto INSTALAR_OPENVPN
if %_openvpn%==2 goto COPIAR_OPENVPN
if %_openvpn%==3 goto SUBMENU_EIDICO
goto SUBMENU_OPENVPN


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_OPENVPN
cls
echo [INFO] Ejecutando instalador de OpenVPN.
start "" "\\172.30.0.13\areas\0-IT\Open VPN\openvpn-install-2.4.6-I602.exe"
timeout /t 3 >nul
goto SUBMENU_OPENVPN

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:COPIAR_OPENVPN
cls
echo [INFO] Copiando archivos en carpeta config...
xcopy "\\172.30.0.13\areas\0-IT\Open VPN\vicky.key" "C:\Program Files\OpenVPN\config\" /Y >nul
xcopy "\\172.30.0.13\areas\0-IT\Open VPN\vicky.crt" "C:\Program Files\OpenVPN\config\" /Y >nul
xcopy "\\172.30.0.13\areas\0-IT\Open VPN\ems.tlsauth" "C:\Program Files\OpenVPN\config\" /Y >nul
xcopy "\\172.30.0.13\areas\0-IT\Open VPN\client.ovpn" "C:\Program Files\OpenVPN\config\" /Y >nul
xcopy "\\172.30.0.13\areas\0-IT\Open VPN\ca.crt" "C:\Program Files\OpenVPN\config\" /Y >nul

echo [OK] Archivos copiados correctamente.

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_OPENVPN

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:SUBMENU_NITROPDF
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    Nitro PDF Reader'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar Nitro PDF' -NoNewline; Write-Host ' (requiere desactivar antivirus)' -ForegroundColor DarkCyan; ^
 Write-Host ''; ^
 Write-Host '                [2] Ejecutar Patch'; ^
 Write-Host ''; ^
 Write-Host '                [3] Eliminar carpeta descomprimida'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,0]:' -ForegroundColor Green -NoNewline"

choice /C:1230 /N
set "_nitro=%errorlevel%"

if %_nitro%==1 goto CONFIRMACION
if %_nitro%==2 goto PATCH
if %_nitro%==3 goto BORRAR_NITROPDF
if %_nitro%==4 goto SUBMENU_EIDICO
goto SUBMENU_NITROPDF


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:CONFIRMACION
cls
echo [ADVERTENCIA] Antes de instalar Nitro PDF, debe desactivar completamente el antivirus.
echo.
echo El Antivirus se encuentra desactivado? (S/N):
choice /C:SN /N
if errorlevel 2 goto SUBMENU_NITROPDF
if errorlevel 1 goto INSTALAR_NITROPDF
goto SUBMENU_NITROPDF

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:INSTALAR_NITROPDF
cls
echo [INFO] Ejecutando instalador de NitroPDF.

powershell -ExecutionPolicy Bypass -Command ^
"$zipPath = '\\172.30.0.13\areas\0-IT\NitroPDF.zip'; ^
 $destPath = \"$env:USERPROFILE\Desktop\NitroPDF\"; ^
 Expand-Archive -Path $zipPath -DestinationPath $destPath -Force; ^
 Start-Process -FilePath \"$destPath\nitro_pro13_x64.msi\""

timeout /t 3 >nul
goto SUBMENU_NITROPDF

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:PATCH
cls
echo [INFO] Ejecutando patch de NitroPDF.

powershell -ExecutionPolicy Bypass -Command ^
"$desktop = [Environment]::GetFolderPath('Desktop'); ^
 $mainPath = [System.IO.Path]::Combine($desktop, 'NitroPDF'); ^
 $zipPath = [System.IO.Path]::Combine($mainPath, 'Patch.zip'); ^
 $patchPath = [System.IO.Path]::Combine($mainPath, 'Patch'); ^
 Expand-Archive -Path $zipPath -DestinationPath $patchPath -Force; ^
 $exePath = [System.IO.Path]::Combine($patchPath, 'nitropdf.enterprise.pro.x64.13.xx-patch.exe'); ^
 Start-Process -FilePath $exePath"

timeout /t 3 >nul
goto SUBMENU_NITROPDF

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:BORRAR_NITROPDF
cls
echo [INFO] Borrando carpeta NitroPDF extraida en el escritorio.

powershell -ExecutionPolicy Bypass -Command ^
"$desktop = [Environment]::GetFolderPath('Desktop'); ^
 $mainPath = [System.IO.Path]::Combine($desktop, 'NitroPDF'); ^
 if (Test-Path $mainPath) { Remove-Item -Path $mainPath -Recurse -Force } else { Write-Host 'Carpeta NitroPDF no encontrada.' }"

timeout /t 3 >nul
goto SUBMENU_NITROPDF

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:FONDOS_EIDICO
cls
echo [INFO] Copiando fondos de pantalla Eidico en la carpeta Imagenes.

powershell -Command ^
    "$dest = Join-Path ([Environment]::GetFolderPath('MyPictures')) 'Fondos Eidico';" ^
    "Copy-Item -Path '\\172.30.0.13\areas\0-IT\Fondos Eidico' -Destination $dest -Recurse -Force"

echo [OK] Carpeta copiada correctamente.

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_EIDICO


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================



:SUBMENU_TECNICA
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    TECNICA:'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Autodesk AutoCAD 2021'; ^
 Write-Host ''; ^
 Write-Host '                [2] Autodesk Revit 2021'; ^
 Write-Host ''; ^
 Write-Host '                [3] ' -NoNewline; Write-Host 'Crack' -ForegroundColor DarkCyan -NoNewline; Write-Host ' AutoCAD/Revit'; ^
 Write-Host ''; ^
 Write-Host '                [4] Autodesk DWG TrueView 2020'; ^
 Write-Host ''; ^
 Write-Host '                [5] SketchUp'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,5,0]:' -ForegroundColor Green -NoNewline"

choice /C:123450 /N
set "_tecnica=%errorlevel%"

if %_tecnica%==1 goto SUBMENU_AUTOCAD
if %_tecnica%==2 goto SUBMENU_REVIT
if %_tecnica%==3 goto SUBMENU_CRACK
if %_tecnica%==4 goto DWG
if %_tecnica%==5 goto SUBMENU_SKETCHUP
if %_tecnica%==6 goto MENU
goto SUBMENU_TECNICA



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================


:SUBMENU_AUTOCAD
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    Autodesk AutoCAD 2021'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Instalar Autodesk AutoCAD 2021'; ^
 Write-Host ''; ^
 Write-Host '                [2] Aplicar bloqueo en Firewall'; ^
 Write-Host ''; ^
 Write-Host '                [3] Instructivo de instalacion'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu anterior'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,0]:' -ForegroundColor Green -NoNewline"

choice /C:1230 /N
set "_autocad=%errorlevel%"

if %_autocad%==1 goto INSTALAR_CAD
if %_autocad%==2 goto FW_BLOCK_CAD
if %_autocad%==3 goto INSTRUCCIONES_CAD
if %_autocad%==4 goto SUBMENU_TECNICA
goto SUBMENU_AUTOCAD


::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================

:INSTALAR_CAD
cls
echo [INFO] Ejecutando instalador Autodesk AutoCAD 2021.
setlocal

:: Ruta de la Imagen AutoCAD 2021
set "ISO=\\172.30.0.13\it\SOFTWARE\TECNICA\Autodesk.AutoCAD.2021.Multilingual.Incl.Kg\Autodesk_AutoCAD_2021_ML_x64.iso"

echo [INFO] Montando imagen como unidad.
powershell -NoProfile -Command ^
    "$isoPath = '%ISO%';" ^
    "$disk = Mount-DiskImage -ImagePath $isoPath -PassThru;" ^
    "$vol = $disk | Get-Volume;" ^
    "$vol.DriveLetter" > temp_drive.txt

set /p DriveLetter=<temp_drive.txt
del temp_drive.txt

if "%DriveLetter%"=="" (
    echo [ERROR] No se pudo montar la ISO.
    timeout /t 3 >nul
    goto MENU
)

echo [OK] Imagen montada en la unidad %DriveLetter%:

echo [INFO] Ejecutando instalador desde %DriveLetter%:\Setup.exe.
start "" "%DriveLetter%:\Setup.exe"

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_AUTOCAD

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:FW_BLOCK_CAD
cls
echo [INFO] Aplicando bloqueo de Autodesk AutoCAD 2021 en Firewall...
regedit /s "\\172.30.0.13\it\SOFTWARE\TECNICA\Autodesk.AutoCAD.2021.Multilingual.Incl.Kg\fw_block_autocad2021.reg"
echo [OK] Bloqueo aplicado correctamente.

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_AUTOCAD

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:INSTRUCCIONES_CAD
start "" "\\172.30.0.13\it\SOFTWARE\TECNICA\Autodesk.AutoCAD.2021.Multilingual.Incl.Kg\Instrucciones.txt"
goto SUBMENU_AUTOCAD

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:SUBMENU_REVIT

::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================


:SUBMENU_CRACK
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    Crack'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Ejecutar crack'; ^
 Write-Host ''; ^
 Write-Host '                [2] Borrar crack'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Submenu TECNICA'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,0]:' -ForegroundColor Green -NoNewline"

choice /C:120 /N
set "_crackautodesk=%errorlevel%"

if %_crackautodesk%==1 goto CONFIRMACION
if %_crackautodesk%==2 goto BORRAR_CRACK
if %_crackautodesk%==3 goto SUBMENU_TECNICA
goto SUBMENU_CRACK


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:CONFIRMACION
cls
echo [ADVERTENCIA] Antes de ejecutar el crack, debe desactivar completamente el antivirus.
echo.
echo El Antivirus se encuentra desactivado? (S/N):
choice /C:SN /N
if errorlevel 2 goto SUBMENU_CRACK
if errorlevel 1 goto CRACK
goto SUBMENU_CRACK

::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======

:CRACK
cls
echo [INFO] Ejecutando crack de Autodesk AutoCAD / Autodesk Revit.

powershell -ExecutionPolicy Bypass -Command ^
"$desktop = [Environment]::GetFolderPath('Desktop'); ^
 $extractPath = [System.IO.Path]::Combine($desktop, 'Crack'); ^
 $zipPath = '\\172.30.0.13\it\SOFTWARE\TECNICA\Autodesk.AutoCAD.2021.Multilingual.Incl.Kg\Crack.zip'; ^
 Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force; ^
 $exePath = [System.IO.Path]::Combine($extractPath, 'xf-adesk20_v2.exe'); ^
 Start-Process -FilePath $exePath"

timeout /t 3 >nul
goto SUBMENU_CRACK

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================

:BORRAR_CRACK
cls
echo [INFO] Borrando carpeta Crack extraida en el escritorio.

powershell -ExecutionPolicy Bypass -Command ^
"$desktop = [Environment]::GetFolderPath('Desktop'); ^
 $crackFolder = [System.IO.Path]::Combine($desktop, 'Crack'); ^
 if (Test-Path $crackFolder) { Remove-Item -Path $crackFolder -Recurse -Force } else { Write-Host 'Carpeta Crack no encontrada.' }"

timeout /t 3 >nul
goto SUBMENU_CRACK

::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================



:SUBMENU_IT



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================



:SUBMENU_O365
cls
powershell -Command ^
"Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                    Microsoft Office 365'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] Office 365 ProPlus 2021 - Retail'; ^
 Write-Host ''; ^
 Write-Host '                [2] Project Pro 2021 - Retail'; ^
 Write-Host ''; ^
 Write-Host '                [3] Visio Pro 2021 - Retail'; ^
 Write-Host ''; ^
 Write-Host '                [4] Microsoft Activation Scripts' -ForegroundColor DarkCyan; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Regresar al Menu Principal'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,0]:' -ForegroundColor Green -NoNewline"

choice /C:12340 /N
set "_office365=%errorlevel%"

if %_office365%==1 goto O365_2021
if %_office365%==2 goto PROJECT_2021
if %_office365%==3 goto VISIO_2021
if %_office365%==4 goto MAS
if %_office365%==5 goto MENU
goto SUBMENU_O365



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================


:O365_2021
cls
echo [INFO] Ejecutando instalador Office 365 ProPlus 2021 Retail.
setlocal

:: Ruta de la imagen O365 2021
set "ISO=\\172.30.0.13\it\SOFTWARE\Microsoft\Office\O365ProPlus2021Retail.img"

echo [INFO] Montando imagen como unidad...
powershell -Command ^
    "$disk = Mount-DiskImage -ImagePath '%ISO%' -PassThru; $vol = $disk | Get-Volume; $vol.DriveLetter" > temp_O365_2021.txt

set /p DriveLetter=<temp_O365_2021.txt
del temp_O365_2021.txt

echo [OK] Imagen montada en la unidad %DriveLetter%:

echo [INFO] Ejecutando instalador desde %DriveLetter%:\Office\Setup64.exe.
start "" "%DriveLetter%:\Office\Setup64.exe"

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_O365


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:PROJECT_2021
cls
echo [INFO] Ejecutando instalador Project Pro 2021 Retail.
setlocal

:: Ruta de la imagen Project 2019
set "ISO=\\172.30.0.13\it\SOFTWARE\Microsoft\Office\ProjectPro2021Retail.img"

echo [INFO] Montando imagen como unidad.
powershell -Command ^
    "$disk = Mount-DiskImage -ImagePath '%ISO%' -PassThru; $vol = $disk | Get-Volume; $vol.DriveLetter" > temp_Project_2021.txt

set /p DriveLetter=<temp_Project_2021.txt
del temp_Project_2021.txt

echo [OK] Imagen montada en la unidad %DriveLetter%:

echo [INFO] Ejecutando instalador desde %DriveLetter%:\Office\Setup64.exe.
start "" "%DriveLetter%:\Office\Setup64.exe"

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_O365


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:VISIO_2021
cls
echo [INFO] Ejecutando instalador Project Pro 2021 Retail.
setlocal

:: Ruta de la imagen Visio 2021
set "ISO=\\172.30.0.13\it\SOFTWARE\Microsoft\Office\VisioPro2021Retail.img"

echo [INFO] Montando imagen como unidad.
powershell -Command ^
    "$disk = Mount-DiskImage -ImagePath '%ISO%' -PassThru; $vol = $disk | Get-Volume; $vol.DriveLetter" > temp_Visio_2021.txt

set /p DriveLetter=<temp_Visio_2021.txt
del temp_Visio_2021.txt

echo [OK] Imagen montada en la unidad %DriveLetter%:

echo [INFO] Ejecutando instalador desde %DriveLetter%:\Office\Setup64.exe.
start "" "%DriveLetter%:\Office\Setup64.exe"

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_O365


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================


:MAS
cls
echo [INFO] Ejecutando Microsoft Activation Scripts desde archivo KMS.bat.
set "scriptPath=%~dp0"
call "%scriptPath%KMS.bat"

:: Cuenta regresiva (5 segundos) antes de volver al submenu
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto SUBMENU_O365


::======================================================================================================================================================================
::======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======    ======
::======================================================================================================================================================================



:ADOBE
cls
echo [INFO] Ejecutando instalador Adobe Creative Cloud Collecction 2022.
setlocal

:: Ruta de la imagen Adobe 2022
set "ISO=\\172.30.0.13\it\SOFTWARE\Adobe2022\Adobe.Master.Collection.CC.2022.v03.02.2022.Multilingual.Win-x64.iso"

echo [INFO] Montando imagen como unidad.
powershell -Command ^
    "$disk = Mount-DiskImage -ImagePath '%ISO%' -PassThru; $vol = $disk | Get-Volume; $vol.DriveLetter" > temp_Adobe_2022.txt

set /p DriveLetter=<temp_Adobe_2022.txt
del temp_Adobe_2022.txt

echo [OK] Imagen montada en la unidad %DriveLetter%:

echo [INFO] Ejecutando instalador desde %DriveLetter%:\Set-up.exe.
start "" "%DriveLetter%:\Set-up.exe"

:: Cuenta regresiva de regreso (5 segundos)
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto MENU



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================



:CREDENCIALES
cls
echo [INFO] Ejecutando Credenciales de Fox.bat.
set "scriptPath=%~dp0"
start "" cmd /c ""%scriptPath%Credenciales de Fox.bat""

:: Cuenta regresiva (5 segundos) antes de volver al submenu
setlocal enabledelayedexpansion
for /L %%i in (5,-1,1) do (
    <nul set /p=[2K[1G[REGRESANDO] Regresando al menu en %%i segundos.
    timeout /t 1 >nul
)
endlocal
goto MENU



::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================
::======================================================================================================================================================================