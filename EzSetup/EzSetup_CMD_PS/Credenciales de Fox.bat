echo off
:: Solicitar privilegios de administrador
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if %errorlevel% NEQ 0 (
    echo Set UAC = CreateObject^("Shell.Application"^) : UAC.ShellExecute "%~s0", "", "", "runas", 1 > "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /b
)

::==================================================================================================================================================================

:: Configuracion de ventana
title Credenciales de Fox
mode con: cols=80 lines=29
cls

::==================================================================================================================================================================

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
 Write-Host '                    CREDENCIALES DE FOX'; ^
 Write-Host ''; ^
 Write-Host ''; ^
 Write-Host '                [1] AWS          ^|  \\172.31.11.146\\Fileserver'; ^
 Write-Host ''; ^
 Write-Host '                [2] Fox Externo  ^|  \\172.30.0.13'; ^
 Write-Host ''; ^
 Write-Host '                [3] Agregar ambos'; ^
 Write-Host ''; ^
 Write-Host '                [4] Abrir Administrador de Credenciales'; ^
 Write-Host '                ________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '                [0] Salir'; ^
 Write-Host '          ____________________________________________________________'; ^
 Write-Host ''; ^
 Write-Host '            Ingrese una opcion con el teclado [1,2,3,4,5,0]:' -ForegroundColor Green -NoNewline"

choice /C:12340 /N
set _opt=%errorlevel%

if %_opt%==1 goto AWS
if %_opt%==2 goto FOX
if %_opt%==3 goto BOTH
if %_opt%==4 goto CREDMAN
if %_opt%==5 exit

goto MENU

:AWS
cls
call :AWS_DIRECT
goto MENU

:FOX
cls
call :FOX_DIRECT
goto MENU

:BOTH
cls
call :AWS_DIRECT
call :FOX_DIRECT
goto MENU

:CREDMAN
explorer.exe shell:::{1206F5F1-0569-412C-8FEC-3204630DFB70}
goto MENU

:AWS_DIRECT
echo [INFO] Registrando credenciales AWS...
cmdkey /add:172.31.11.146 /user:foxeidico /pass:76EgzgQRCmIZBWy >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron registrar las credenciales AWS.
    exit /b
)
echo [OK] Credenciales AWS registradas.
echo [INFO] Creando acceso directo...
set "shortcutPath=%USERPROFILE%\Desktop\Fileserver (172.31.11.146).lnk"
set "targetPath=\\172.31.11.146\Fileserver"
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%shortcutPath%'); $s.TargetPath='%targetPath%'; $s.Description='Fileserver (\\172.31.11.146)'; $s.Save()" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el acceso directo.
) else (
    echo [OK] Acceso directo creado.
)
exit /b

:FOX_DIRECT
echo [INFO] Registrando credenciales Fox Externo...
cmdkey /add:172.30.0.13 /user:eidico\fexterno /pass:clDBEPJ@jT2abal >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se pudieron registrar las credenciales Fox.
    exit /b
)
echo [OK] Credenciales Fox registradas.
echo [INFO] Creando acceso directo...
set "shortcutPath=%USERPROFILE%\Desktop\FILESERVER.lnk"
set "targetPath=\\172.30.0.13"
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%shortcutPath%'); $s.TargetPath='%targetPath%'; $s.Description='Fileserver (\\172.30.0.13)'; $s.IconLocation='C:\Windows\System32\shell32.dll,15'; $s.Save()" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el acceso directo.
) else (
    echo [OK] Acceso directo creado.
)
exit /b
