#!/bin/zsh
# ============================================================
# start.command  --  macOS twin of start.vbs.
#
# Double-click from Finder (or run from a terminal) to start the
# server *detached* and open the web UI in your default browser.
# The server writes to server.log in this folder. Use stop.command
# to shut it down.
# ============================================================
cd "$(dirname "$0")" || exit 1

# Homebrew + ~/.local/bin so marp / npx / claude / codex resolve when
# launched from Finder (which does not source shell profiles).
export PATH="/opt/homebrew/bin:$HOME/.local/bin:$PATH"

URL="http://127.0.0.1:8765/"
PY=".venv/bin/python"

if [ ! -f server.py ]; then
    echo "server.py not found in $(pwd)" >&2
    exit 1
fi
if [ ! -x "$PY" ]; then
    echo "No Python found in .venv. Run setup first (see README)." >&2
    exit 1
fi

# Already running? Just open the browser.
if curl -s --max-time 2 "${URL}healthz" > /dev/null 2>&1; then
    echo "Server already running at $URL"
    open "$URL"
    exit 0
fi

nohup "$PY" server.py >> server.log 2>&1 &
disown

# Give the server a moment to bind, then open the browser.
for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.5
    if curl -s --max-time 2 "${URL}healthz" > /dev/null 2>&1; then
        echo "Server up at $URL (logs: server.log)"
        open "$URL"
        exit 0
    fi
done

echo "Server did not come up within 5s - check server.log" >&2
exit 1
