#!/bin/zsh
# ============================================================
# serve.command  --  macOS twin of serve.cmd.
#
# Runs the server in the foreground with a visible terminal
# (debugging). Keep the window open while you use the web UI;
# Ctrl+C (or close the window) to stop. Crashes auto-restart
# up to 5 times, mirroring serve.cmd.
# ============================================================
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

PY=".venv/bin/python"
RETRIES=0
MAX_RETRIES=5

echo ""
echo "===================================================="
echo " Riverfed - Markdown server"
echo " Keep this window open while you use the web UI."
echo " Press Ctrl+C (or close this window) to stop."
echo " Logs are mirrored to: $(pwd)/server.log"
echo "===================================================="
echo ""

while true; do
    if [ -x "$PY" ]; then
        "$PY" server.py "$@"
    else
        python3 server.py "$@"
    fi
    EXITCODE=$?

    echo ""
    if [ $EXITCODE -eq 0 ]; then
        echo "Server stopped cleanly."
        break
    fi

    RETRIES=$((RETRIES + 1))
    echo "Server exited with code $EXITCODE (attempt $RETRIES of $MAX_RETRIES)."
    if [ $RETRIES -ge $MAX_RETRIES ]; then
        echo "Reached max restart attempts. Check server.log for the cause."
        break
    fi
    echo "Restarting in 3 seconds. Press Ctrl+C now to abort."
    sleep 3
done
