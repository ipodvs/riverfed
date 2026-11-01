#!/bin/zsh
# ============================================================
# stop.command  --  macOS twin of stop.cmd.
#
# Stops whatever is listening on port 8765 (the server only -
# never touches claude / codex / other python processes).
# ============================================================
echo "Looking for server on port 8765..."

PID=$(lsof -ti tcp:8765 -sTCP:LISTEN 2>/dev/null | head -1)

if [ -z "$PID" ]; then
    echo "No server is currently listening on port 8765."
    exit 0
fi

echo "Stopping PID $PID..."
kill "$PID" 2>/dev/null
sleep 1
if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" 2>/dev/null
    sleep 1
fi

if kill -0 "$PID" 2>/dev/null; then
    echo "Could not stop PID $PID. You may need to kill it manually." >&2
    exit 1
fi
echo "Server stopped."
