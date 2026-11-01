@echo off
setlocal

rem Probe the server. If it responds, exit 0 quietly.
rem If it does not respond, check if something is already listening on 8765.
rem   - Something is listening but healthz failed: leave it alone (human's job).
rem   - Nothing is listening: relaunch via start.vbs.

curl -s -o NUL --max-time 8 http://127.0.0.1:8765/healthz
if %ERRORLEVEL% EQU 0 (
    rem Server is healthy. Nothing to do.
    exit /b 0
)

rem healthz probe failed. Check if anything is listening on 8765.
set "LISTENING="
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8765 " ^| findstr LISTENING') do (
    set "LISTENING=%%a"
)

if not "%LISTENING%"=="" (
    rem Something is listening but healthz is down. Leave it for a human.
    echo Watchdog: process %LISTENING% is listening on 8765 but /healthz failed. Skipping.
    exit /b 1
)

rem Nothing is listening. Relaunch the server silently.
echo Watchdog: nothing on 8765. Launching server via start.vbs.
wscript.exe "%~dp0start.vbs"

endlocal
exit /b 0
