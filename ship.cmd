@echo off
REM ============================================================
REM ship.cmd  --  Push your local commits to GitHub.
REM
REM Run this at the END of a work session. It:
REM   1. Stops if you have uncommitted work (commit it first).
REM   2. Pulls latest with rebase (so your push won't be rejected).
REM   3. Pushes your local commits to origin/main.
REM
REM Safe to double-click from Explorer.
REM ============================================================
setlocal enableextensions
cd /d "%~dp0"
title Riverfed - ship

echo.
echo === Shipping local commits to origin/main ===
echo.

REM 1. Bail if there are uncommitted changes.
git diff --quiet
set DIRTY_UNSTAGED=%ERRORLEVEL%
git diff --cached --quiet
set DIRTY_STAGED=%ERRORLEVEL%
if not "%DIRTY_UNSTAGED%"=="0" goto :dirty
if not "%DIRTY_STAGED%"=="0" goto :dirty

REM 2. Show what we're about to ship
git fetch origin
if errorlevel 1 (
    echo *** git fetch failed. Check your network or GitHub auth.
    goto :end
)

echo.
echo --- Local commits ahead of origin ---
git log --oneline --pretty="  %%h: %%s" origin/main..HEAD
echo.

REM Detect "nothing to push" early
for /f %%C in ('git rev-list --count origin/main..HEAD') do set AHEAD=%%C
if "%AHEAD%"=="0" (
    echo Nothing to push - local is already at origin/main.
    git log -1 --pretty="  HEAD is %%h - %%an: %%s"
    goto :end
)

REM 3. Sync first (rebase any incoming commits underneath ours)
echo --- Syncing with origin first (rebase) ---
git pull --rebase origin main
if errorlevel 1 (
    echo.
    echo *** Rebase hit a conflict.
    echo     Open the conflicting files, resolve the markers ^(^<^<^<^<^<^<^<^),
    echo     then run:
    echo         git add ^<resolved-files^>
    echo         git rebase --continue
    echo         ship.cmd
    echo.
    echo     Or abort with:  git rebase --abort
    goto :end
)

REM 4. Push
echo.
echo --- Pushing ---
git push origin main
if errorlevel 1 (
    echo.
    echo *** Push failed. See output above.
    echo     The most common cause is GitHub auth - try running:
    echo         git push
    echo     manually in a terminal to see the auth prompt.
    goto :end
)

echo.
echo === Shipped ===
git log --pretty="  %%h: %%s" -3
goto :end

:dirty
echo *** You have uncommitted local changes:
git status --short
echo.
echo Commit them first, then re-run ship.cmd.
echo   git add .
echo   git commit -m "your message"
echo Or temporarily set them aside with:
echo   git stash
echo.

:end
echo.
pause
endlocal
