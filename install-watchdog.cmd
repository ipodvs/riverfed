@echo off
setlocal

set "TASKNAME=RiverfedWatchdog"
set "VBSPATH=%~dp0watchdog.vbs"

echo Registering scheduled task: %TASKNAME%
echo Script: %VBSPATH%

schtasks /Create /TN "%TASKNAME%" /TR "wscript.exe \"%VBSPATH%\"" /SC MINUTE /MO 5 /F

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: schtasks /Create failed with exit code %ERRORLEVEL%.
    echo The watchdog scripts are in place but the task was not registered.
    echo Try running this script as Administrator if you see an access error.
    goto end
)

echo.
echo Task registered successfully. Verifying...
echo.
schtasks /Query /TN "%TASKNAME%"

echo.
echo Watchdog is active. It will probe http://127.0.0.1:8765/healthz every 5 minutes
echo and relaunch the server automatically if it is not responding.

:end
echo.
pause
endlocal
