@echo off
setlocal
title Stop Youtuber server
echo Looking for server on port 8765...

set "PID="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8765 " ^| findstr LISTENING') do (
    set "PID=%%a"
)

if "%PID%"=="" (
    echo No server is currently listening on port 8765.
    goto end
)

echo Stopping PID %PID%...
taskkill /PID %PID% /F >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Server stopped.
) else (
    echo Could not stop PID %PID%. You may need to kill it manually.
)

:end
echo.
echo Press any key to close this window...
pause >nul
endlocal
