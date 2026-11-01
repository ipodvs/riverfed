@echo off
REM ============================================================
REM sync-vaults.cmd  --  Share the knowledge bases.
REM
REM The vaults live OUTSIDE this repo (~/RiverfedVaults), each as
REM its own git repo. This commits whatever ingests/edits happened
REM locally, pulls your brother's edits, and pushes yours.
REM
REM Run it whenever you want the other person to see your latest
REM wiki state (after a few ingests, end of a session, etc).
REM Safe to double-click from Explorer.
REM ============================================================
setlocal enableextensions
cd /d "%~dp0"
title Riverfed - sync vaults

echo.
echo === Syncing knowledge-base vaults ===
echo.

py -3.13 wiki\scripts\sync_vaults.py

echo.
pause
endlocal
