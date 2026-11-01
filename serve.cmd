@echo off
setlocal enabledelayedexpansion
title Youtuber Server  (do not close this window)
set "SCRIPT_DIR=%~dp0"
set "PY_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
set RETRIES=0
set MAX_RETRIES=5

echo.
echo ====================================================
echo  Youtuber - Markdown server
echo  Keep this window open while you use the web UI.
echo  Press Ctrl+C twice (or close this window) to stop.
echo  Logs are mirrored to:  %SCRIPT_DIR%server.log
echo ====================================================
echo.

:loop
if exist "%PY_EXE%" (
    "%PY_EXE%" "%SCRIPT_DIR%server.py" %*
) else (
    py -3.13 "%SCRIPT_DIR%server.py" %*
)
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE% EQU 0 (
    echo Server stopped cleanly.
    goto end
)

set /a RETRIES+=1
echo Server exited with code %EXITCODE% (attempt !RETRIES! of %MAX_RETRIES%).
if !RETRIES! GEQ %MAX_RETRIES% (
    echo Reached max restart attempts. Check %SCRIPT_DIR%server.log for the cause.
    goto end
)
echo Restarting in 3 seconds. Press Ctrl+C now to abort.
timeout /t 3 >nul 2>&1
goto loop

:end
echo.
echo Press any key to close this window...
pause >nul
endlocal
