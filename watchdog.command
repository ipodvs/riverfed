#!/bin/zsh
# ============================================================
# watchdog.command  --  macOS twin of watchdog.cmd.
#
# Probe the server. If it responds, poke the watcher heartbeat, then exit.
# If it does not respond, check if something is already listening on 8765.
#   - Something is listening but healthz failed: leave it alone (human's job).
#   - Nothing is listening: relaunch the launchd server job.
#
# Run every 5 minutes by the com.riverfed.watchdog LaunchAgent
# (see install-watchdog.command). Output goes to the launchd log.
# ============================================================

BASE="http://127.0.0.1:8765"
URL="$BASE/healthz"
JOB="com.riverfed.server"

# Server healthy? Poke the auto-ingest watcher heartbeat, then done. The
# server only actually sweeps when a channel is overdue (interval-guarded),
# so this external tick makes auto-ingest self-healing even if the server's
# in-process sweep thread has stalled — the failure we hit 2026-08-05.
if curl -s -o /dev/null --max-time 8 "$URL"; then
    curl -s -o /dev/null --max-time 20 -X POST "$BASE/watcher/tick" || true
    exit 0
fi

# healthz probe failed. Is anything still listening on 8765?
LISTENING=$(lsof -ti tcp:8765 -sTCP:LISTEN 2>/dev/null | head -1)

if [ -n "$LISTENING" ]; then
    # Something is bound but unhealthy. Leave it for a human.
    echo "$(date '+%Y-%m-%d %H:%M:%S') Watchdog: pid $LISTENING is listening on 8765 but /healthz failed. Skipping."
    exit 1
fi

# Nothing is listening. Kickstart the launchd server job (restarts if loaded,
# -k kills any stale instance first). Keeps the server under launchd's control
# instead of spawning an unmanaged detached copy.
echo "$(date '+%Y-%m-%d %H:%M:%S') Watchdog: nothing on 8765. Kickstarting $JOB."
launchctl kickstart -k "gui/$(id -u)/$JOB"
exit 0
