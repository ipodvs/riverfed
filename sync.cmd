@echo off
REM ============================================================
REM sync.cmd  --  Pull the latest from GitHub before you start work.
REM
REM Run this at the START of every session. If your brother has
REM pushed anything, you'll have it. If you have uncommitted local
REM changes, the script tells you to commit or stash first.
REM
REM Safe to double-click from Explorer.
REM ============================================================
setlocal enableextensions
cd /d "%~dp0"
title Riverfed - sync

echo.
echo === Pulling latest from origin/main ===
echo.

REM 1. Bail if there are uncommitted changes - rebase would refuse.
git diff --quiet
set DIRTY_UNSTAGED=%ERRORLEVEL%
git diff --cached --quiet
set DIRTY_STAGED=%ERRORLEVEL%
if not "%DIRTY_UNSTAGED%"=="0" goto :dirty
if not "%DIRTY_STAGED%"=="0" goto :dirty

REM 2. Fetch + rebase
git fetch origin
if errorlevel 1 (
    echo *** git fetch failed. Check your network or GitHub auth.
    goto :end
)

REM 3. Show what's about to come in
echo.
echo --- Incoming commits from origin ---
git log --oneline --pretty="  %%h %%an: %%s" HEAD..origin/main
echo.

git pull --rebase origin main
if errorlevel 1 (
    echo.
    echo *** Rebase hit a conflict.
    echo     Open the conflicting files, resolve the markers ^(^<^<^<^<^<^<^<^),
    echo     then run:
    echo         git add ^<resolved-files^>
    echo         git rebase --continue
    echo.
    echo     Or abort with:  git rebase --abort
    goto :end
)

echo.
echo === Up to date ===
git log -1 --pretty="  HEAD is %%h - %%an: %%s"
goto :end

:dirty
echo *** You have uncommitted local changes:
git status --short
echo.
echo Commit them first, then re-run sync.cmd.
echo   git add .
echo   git commit -m "your message"
echo Or temporarily set them aside with:
echo   git stash
echo.

:end
echo.
pause
endlocal
