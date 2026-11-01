@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%convert.py" %*
) else (
    py -3.13 "%SCRIPT_DIR%convert.py" %*
)
endlocal
