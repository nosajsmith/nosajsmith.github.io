@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  MacArthur War Engine - MWE_Bridge Fix
echo  Requires: Admin, NSSM, Python 3.13
echo ============================================
echo.

REM --- CONFIGURE THESE PATHS IF NEEDED ---
set "SERVICE_NAME=MWE_Bridge"
set "NSSM_EXE=C:\Tools\NSSM\nssm.exe"
set "PYTHON_EXE=C:\Program Files\Python313\python.exe"
set "BRIDGE_DIR=C:\MWE\server"
set "BRIDGE_SCRIPT=C:\MWE\server\mwe_bridge_p8.py"
set "LOG_DIR=C:\MWE\logs"
set "WS_PORT=8766"
REM ---------------------------------------

echo [1] Stopping service %SERVICE_NAME%...
"%NSSM_EXE%" stop %SERVICE_NAME% >nul 2>&1

echo [2] Checking if port %WS_PORT% is in use...
set "PORT_PID="

for /f "tokens=5" %%a in ('netstat -ano ^| find ":%WS_PORT%" ^| find "LISTENING"') do (
    set "PORT_PID=%%a"
)

if defined PORT_PID (
    echo     Port %WS_PORT% is in use by PID !PORT_PID!.
    echo     Showing process info:
    tasklist /FI "PID eq !PORT_PID!"
    echo     Attempting to kill PID !PORT_PID! ...
    taskkill /PID !PORT_PID! /F >nul 2>&1
    if %ERRORLEVEL%==0 (
        echo     Successfully killed PID !PORT_PID!.
    ) else (
        echo     WARNING: Could not kill PID !PORT_PID!. Check manually.
    )
) else (
    echo     Port %WS_PORT% is free.
)

echo.
echo [3] Ensuring log directory exists: %LOG_DIR%
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo     Created %LOG_DIR%.
) else (
    echo     Already exists.
)

echo.
echo [4] Setting NSSM parameters for %SERVICE_NAME%...

"%NSSM_EXE%" set %SERVICE_NAME% Application "%PYTHON_EXE%"
"%NSSM_EXE%" set %SERVICE_NAME% AppParameters "%BRIDGE_SCRIPT%"
"%NSSM_EXE%" set %SERVICE_NAME% AppDirectory "%BRIDGE_DIR%"
"%NSSM_EXE%" set %SERVICE_NAME% AppStdout "%LOG_DIR%\service_stdout.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppStderr "%LOG_DIR%\service_stderr.log"
"%NSSM_EXE%" set %SERVICE_NAME% AppEnvironmentExtra "PYTHONUNBUFFERED=1"

echo     NSSM configuration updated.
echo.

echo [5] Ensuring Python dependencies (websockets, aiohttp) are installed...
"%PYTHON_EXE%" -m pip install websockets aiohttp
echo.

echo [6] Starting service %SERVICE_NAME%...
"%NSSM_EXE%" start %SERVICE_NAME% >nul 2>&1

echo [7] Querying service state:
sc query %SERVICE_NAME%
echo.

echo [8] Showing last 20 lines of stderr log (if present)...
powershell -Command "if (Test-Path '%LOG_DIR%\service_stderr.log') { Get-Content -Path '%LOG_DIR%\service_stderr.log' -Tail 20 } else { Write-Output 'No stderr log found yet.' }"
echo.

echo [9] Done.
echo If the service is not RUNNING above, check the stderr log and fix the reported error.
echo ============================================
echo  Script finished.
echo ============================================

endlocal
pause
