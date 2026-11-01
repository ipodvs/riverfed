@echo off
setlocal

set "TASKNAME=RiverfedWatchdog"

echo Removing scheduled task: %TASKNAME%
schtasks /Delete /F /TN "%TASKNAME%"

if %ERRORLEVEL% EQU 0 (
    echo Task removed successfully.
) else (
    echo Task not found or could not be removed (exit code %ERRORLEVEL%).
)

echo.
pause
endlocal
